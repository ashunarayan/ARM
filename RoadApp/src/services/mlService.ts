import { MLInput, SensorReading } from '../types';
const scalerParams = require('../assets/scaler_params.json');

export class MLService {
    private static model: any = null;
    private static interpreter: any = null;

    static async loadModel(): Promise<void> {
        if (this.model) {
            return;
        }

        try {
            // TFLite temporarily disabled due to build issues
            // Will use mock predictions for now
            this.model = { loaded: true };
            console.log('ML model mock loaded successfully');
        } catch (error) {
            console.error('Failed to load ML model:', error);
            throw error;
        }
    }

    private static createWindow(readings: SensorReading[], windowSize: number = 20): { raw: number[][], stats: number[] } | null {
        if (readings.length < windowSize) {
            return null;
        }

        const window = readings.slice(-windowSize);
        const featureCols = ['ax', 'ay', 'az', 'wx', 'wy', 'wz', 'speed'];

        const rawData: number[][] = window.map(reading => [
            reading.ax, reading.ay, reading.az,
            reading.wx, reading.wy, reading.wz,
            reading.speed
        ]);

        const statsRow: number[] = [];
        featureCols.forEach(col => {
            const series = window.map(r => r[col as keyof SensorReading]);
            const mean = series.reduce((a, b) => a + b, 0) / series.length;
            const variance = series.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / series.length;
            const std = Math.sqrt(variance);
            const rms = Math.sqrt(series.reduce((a, b) => a + b * b, 0) / series.length);
            const range = Math.max(...series) - Math.min(...series);

            const n = series.length;
            const m3 = series.reduce((a, b) => a + Math.pow(b - mean, 3), 0) / n;
            const m4 = series.reduce((a, b) => a + Math.pow(b - mean, 4), 0) / n;
            const skew = std === 0 ? 0 : m3 / Math.pow(std, 3);
            const kurt = std === 0 ? 0 : (m4 / Math.pow(std, 4)) - 3;

            statsRow.push(mean, std, rms, range, isNaN(skew) ? 0 : skew, isNaN(kurt) ? 0 : kurt);
        });

        return { raw: rawData, stats: statsRow };
    }

    private static normalizeData(raw: number[][], stats: number[]): { rawNorm: Float32Array, statsNorm: Float32Array } {
        const rawMean = scalerParams.raw_scaler.mean;
        const rawStd = scalerParams.raw_scaler.std;
        const statsMean = scalerParams.stats_scaler.mean;
        const statsStd = scalerParams.stats_scaler.std;

        const rawFlat = raw.flat();
        const rawNormalized = rawFlat.map((val, idx) => {
            const featIdx = idx % 7;
            return (val - rawMean[featIdx]) / rawStd[featIdx];
        });

        const statsNormalized = stats.map((val, idx) => {
            return (val - statsMean[idx]) / statsStd[idx];
        });

        return {
            rawNorm: new Float32Array(rawNormalized),
            statsNorm: new Float32Array(statsNormalized.map(v => isNaN(v) ? 0 : v))
        };
    }

    static async predict(input: MLInput): Promise<0 | 1 | 2 | 3> {
        if (!this.model) {
            await this.loadModel();
        }

        try {
            const window = this.createWindow(input.readings, 20);
            if (!window) {
                console.warn('Insufficient sensor readings for prediction');
                return 1;
            }

            // Mock prediction based on statistical features
            // In production, this would use TFLite model
            const { stats } = window;
            const avgAccel = (stats[0] + stats[6] + stats[12]) / 3; // avg of ax, ay, az means

            // Simple heuristic for road quality
            if (avgAccel < 0.5) return 0; // Excellent
            if (avgAccel < 1.5) return 1; // Good
            if (avgAccel < 2.5) return 2; // Fair
            return 3; // Poor

        } catch (error) {
            console.error('ML prediction failed:', error);
            return 1;
        }
    }

    static unloadModel(): void {
        this.model = null;
        this.interpreter = null;
    }
}
