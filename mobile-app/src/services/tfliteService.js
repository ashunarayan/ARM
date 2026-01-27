/**
 * TensorFlow Lite Inference Service
 * 
 * Loads the TFLite model and runs on-device inference using react-native-fast-tflite
 * - Model: Hybrid CNN for road quality classification
 * - Input 1: 42 Statistical features
 * - Input 2: 20x7 sensor matrix
 * - Output: Integer classification (0-3)
 */

import { loadTensorflowModel } from 'react-native-fast-tflite';
import * as FileSystem from 'expo-file-system';
import { Asset } from 'expo-asset';

// Helper for loading local assets
const loadAsset = async (module) => {
    const asset = Asset.fromModule(module);
    await asset.downloadAsync();
    return asset.localUri;
};

// Math helpers
const mean = (data) => data.reduce((a, b) => a + b, 0) / data.length;

const std = (data, m) => {
    const mu = m || mean(data);
    const sumSqDiff = data.reduce((a, b) => a + Math.pow(b - mu, 2), 0);
    return Math.sqrt(sumSqDiff / data.length);
};

const rms = (data) => {
    const sumSq = data.reduce((a, b) => a + Math.pow(b, 2), 0);
    return Math.sqrt(sumSq / data.length);
};

const range = (data) => Math.max(...data) - Math.min(...data);

// Unbiased Skewness
const skewness = (data, m, s) => {
    const n = data.length;
    if (n < 3) return 0;
    const mu = m || mean(data);
    const sigma = s || std(data, mu);
    const m3 = data.reduce((a, b) => a + Math.pow(b - mu, 3), 0) / n;
    const g1 = m3 / Math.pow(sigma, 3);
    return (Math.sqrt(n * (n - 1)) / (n - 2)) * g1;
};

// Unbiased Kurtosis
const kurtosis = (data, m, s) => {
    const n = data.length;
    if (n < 4) return 0;
    const mu = m || mean(data);
    const sigma = s || std(data, mu);
    const m2 = Math.pow(sigma, 2);
    const m4 = data.reduce((a, b) => a + Math.pow(b - mu, 4), 0) / n;
    const kFactor1 = (n - 1) / ((n - 2) * (n - 3));
    const kFactor2 = (n + 1) * (m4 / Math.pow(m2, 2)) - 3 * (n - 1);
    return kFactor1 * kFactor2;
};

class TFLiteInferenceService {
    constructor() {
        this.model = null;
        this.scalerParams = null;
        this.isReadyStatus = false;
        this.featureOrder = [0, 1, 2, 3, 4, 5, 6]; // Indices for ax, ay, az, wx, wy, wz, speed
    }

    async initialize() {
        try {
            console.log(' Initializing ML Service (Fast TFLite)...');
            
            // Load Scaler Params
            this.scalerParams = require('../../assets/ml-model/scaler_params.json');

            // Load TFLite Model
            const modelAsset = require('../../assets/ml-model/model.tflite');
            const modelUri = await loadAsset(modelAsset);
            
            this.model = await loadTensorflowModel(modelUri);
            this.isReadyStatus = true;
            console.log(' ML Service initialized successfully');
        } catch (error) {
            console.error(' Failed to initialize ML model:', error);
            throw error;
        }
    }

    async runInference(sensorMatrix) {
        if (!this.isReadyStatus || !this.model) {
            console.warn('Model not ready');
            return -1;
        }

        try {
            // 1. Extract Features & Normalize
            const { rawInput, statsInput } = this.preprocess(sensorMatrix);

            // 2. Run Inference
            // Input order: [stats, raw] based on notebook
            // Cast to Float32Array explicitly usually required by fast-tflite if passing array?
            // Actually run takes variable args? No, typically an array of tensors data buffers.
            // Check library docs mental model: typically run(inputs: ArrayBufferView[]) or similar.
            // fast-tflite run takes single argument `inputs: any[]`.
            
            const results = await this.model.run([statsInput, rawInput]);
            
            // 3. Interpret Output
            if (results && results[0]) {
                const probabilities = results[0]; // TypedArray
                let maxProb = -1;
                let predictedClass = -1;
                
                for (let i = 0; i < probabilities.length; i++) {
                    if (probabilities[i] > maxProb) {
                        maxProb = probabilities[i];
                        predictedClass = i;
                    }
                }
                return predictedClass;
            }
            return -1;

        } catch (error) {
            console.error('Inference failed:', error);
            return -1;
        }
    }

    // Helper for mock (unused but kept for API compat if needed)
    async runMockInference(sensorMatrix) {
        return 0; 
    }

    preprocess(sensorMatrix) {
        // sensorMatrix is 20x7 array
        // We need to calculate stats for each column (channel)
        
        const statsFlat = [];
        const rawFlat = []; // Just flattened matrix

        const numRows = sensorMatrix.length; // 20
        const numCols = 7;

        // Iterate columns
        for (let col = 0; col < numCols; col++) {
            const series = [];
            for (let row = 0; row < numRows; row++) {
                const val = sensorMatrix[row][col];
                series.push(val);
                // We construct rawFlat row by row usually for TFLite memory layout [1, 20, 7]
                // So rawFlat logic is separated below to ensure correct order
            }

            // Calculate stats for this column
            const m = mean(series);
            const s = std(series, m);
            let sk = skewness(series, m, s);
            let ku = kurtosis(series, m, s);
            
            if (isNaN(sk)) sk = 0.0;
            if (isNaN(ku)) ku = 0.0;

            statsFlat.push(m);
            statsFlat.push(s);
            statsFlat.push(rms(series));
            statsFlat.push(range(series));
            statsFlat.push(sk);
            statsFlat.push(ku);
        }

        // Fill Raw Flat (Row-major order)
        for (let row = 0; row < numRows; row++) {
            for (let col = 0; col < numCols; col++) {
                rawFlat.push(sensorMatrix[row][col]);
            }
        }

        // Normalize
        const normRaw = this.normalize(rawFlat, this.scalerParams.raw_scaler, false);
        const normStats = this.normalize(statsFlat, this.scalerParams.stats_scaler, true);

        return {
            rawInput: new Float32Array(normRaw),
            statsInput: new Float32Array(normStats)
        };
    }

    normalize(flatData, scaler, isAllFeatures) {
        const means = scaler.mean;
        const stds = scaler.std;
        const normalized = [];
        
        if (isAllFeatures) {
            // Stats: 42 features -> 42 means
            for (let i = 0; i < flatData.length; i++) {
                normalized.push((flatData[i] - means[i]) / stds[i]);
            }
        } else {
            // Raw: 140 values -> 7 means (repeated)
            const numChannels = means.length; // 7
            for (let i = 0; i < flatData.length; i++) {
                const channelIndex = i % numChannels;
                normalized.push((flatData[i] - means[channelIndex]) / stds[channelIndex]);
            }
        }
        return normalized;
    }

    isReady() {
        return this.isReadyStatus;
    }

    dispose() {
        // Clean up
    }
}

export const tfliteService = new TFLiteInferenceService();
