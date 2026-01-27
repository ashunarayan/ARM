import { loadTensorflowModel } from 'react-native-fast-tflite';
import { ENV } from '../config/env';

// Math helpers
const mean = (data: number[]) => data.reduce((a, b) => a + b, 0) / data.length;

const std = (data: number[], m?: number) => {
    const mu = m || mean(data);
    const sumSqDiff = data.reduce((a, b) => a + Math.pow(b - mu, 2), 0);
    return Math.sqrt(sumSqDiff / data.length);
};

const rms = (data: number[]) => {
    const sumSq = data.reduce((a, b) => a + Math.pow(b, 2), 0);
    return Math.sqrt(sumSq / data.length);
};

const range = (data: number[]) => Math.max(...data) - Math.min(...data);

const skewness = (data: number[], m: number, s: number) => {
    const n = data.length;
    if (n < 3) return 0;
    const m3 = data.reduce((a, b) => a + Math.pow(b - m, 3), 0) / n;
    const g1 = m3 / Math.pow(s, 3);
    return (Math.sqrt(n * (n - 1)) / (n - 2)) * g1;
};

const kurtosis = (data: number[], m: number, s: number) => {
    const n = data.length;
    if (n < 4) return 0;
    const m2 = Math.pow(s, 2);
    const m4 = data.reduce((a, b) => a + Math.pow(b - m, 4), 0) / n;
    const kFactor1 = (n - 1) / ((n - 2) * (n - 3));
    const kFactor2 = (n + 1) * (m4 / Math.pow(m2, 2)) - 3 * (n - 1);
    return kFactor1 * kFactor2;
};

class MLService {
    private model: any = null;
    private scalerParams: any = null;
    private isReady: boolean = false;
    private featureOrder = ['ax', 'ay', 'az', 'wx', 'wy', 'wz', 'speed'];

    async initialize() {
        try {
            console.log('Initializing ML Service...');
            
            // Load Scaler Params
            this.scalerParams = ENV.ML.SCALER_FILE; 

            // Load TFLite Model from assets (bundled)
            // react-native-fast-tflite loads from assets folder by filename
            this.model = await loadTensorflowModel(ENV.ML.MODEL_FILE);
            
            this.isReady = true;
            console.log('ML Model loaded successfully');
        } catch (error) {
            console.error('Failed to load ML model:', error);
        }
    }

    async predict(windowData: any[]) {
        if (!this.isReady || !this.model) {
            console.warn('Model not ready');
            return null;
        }

        try {
            // 1. Extract Features & Normalize
            const { rawInput, statsInput } = this.preprocess(windowData);

            // 2. Run Inference
            const results = await this.model.run([statsInput, rawInput]);
            
            // 3. Interpret Output (Softmax)
            if (results && results[0]) {
                const probabilities = results[0]; 
                // Find argmax
                let maxProb = -1;
                let predictedClass = -1;
                // Helper to iterate typed array or array
                for (let i = 0; i < probabilities.length; i++) {
                    if (probabilities[i] > maxProb) {
                        maxProb = probabilities[i];
                        predictedClass = i;
                    }
                }
                return predictedClass;
            }
            return null;
        } catch (error) {
            console.error('Prediction failed:', error);
            return null;
        }
    }

    preprocess(windowData: any[]) {
        const rawFlat: number[] = [];
        const channelData: Record<string, number[]> = {};
        this.featureOrder.forEach(key => channelData[key] = []);

        // Fill data
        windowData.forEach(sample => {
            this.featureOrder.forEach(key => {
                const val = sample[key] || 0;
                channelData[key].push(val);
                rawFlat.push(val); // Populate raw flat (row-major: s1[all], s2[all]...)
            });
        });

        // Calculate Stats (42 features)
        const statsFlat: number[] = [];
        this.featureOrder.forEach(key => {
            const series = channelData[key];
            const m = mean(series);
            const s = std(series, m);
            let sk = skewness(series, m, s);
            let ku = kurtosis(series, m, s);
            if (isNaN(sk)) sk = 0.0;
            if (isNaN(ku)) ku = 0.0;

            statsFlat.push(m, s, rms(series), range(series), sk, ku);
        });

        // Normalize
        const normRaw = this.normalize(rawFlat, this.scalerParams.raw_scaler, false);
        const normStats = this.normalize(statsFlat, this.scalerParams.stats_scaler, true);

        return {
            rawInput: new Float32Array(normRaw),
            statsInput: new Float32Array(normStats)
        };
    }

    normalize(flatData: number[], scaler: { mean: number[], std: number[] }, isAllFeatures: boolean) {
        const means = scaler.mean;
        const stds = scaler.std;
        const normalized: number[] = [];

        if (isAllFeatures) {
            for (let i = 0; i < flatData.length; i++) {
                normalized.push((flatData[i] - means[i]) / stds[i]);
            }
        } else {
            const numChannels = means.length; 
            for (let i = 0; i < flatData.length; i++) {
                const channelIndex = i % numChannels;
                normalized.push((flatData[i] - means[channelIndex]) / stds[channelIndex]);
            }
        }
        return normalized;
    }
}

export const mlService = new MLService();
