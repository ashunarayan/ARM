/**
 * TensorFlow Lite Service
 * Handles ML model loading and inference
 * 
 * ARCHITECTURE:
 * - Loads model from assets on initialization
 * - Runs inference on preprocessed sensor data
 * - Isolated from UI and API logic
 * - Used by ML service layer
 * 
 * NOTE: TFLite models need to be converted to TensorFlow.js format
 * Use: tensorflowjs_converter --input_format=tf_saved_model --output_format=tfjs_graph_model
 */

import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-react-native';
import { ENV } from '../config/env';
import type { RoadQuality } from '../types';

// Import scaler parameters for preprocessing
const SCALER_PARAMS = require('../../assets/ml-model/scaler_params.json');

class TFLiteService {
    private model: tf.LayersModel | null = null;
    private isModelLoaded = false;
    private isTensorFlowReady = false;

    /**
     * Initialize TensorFlow.js and load the model
     */
    async initialize(): Promise<void> {
        try {
            console.log(' Initializing TensorFlow.js...');

            // Initialize TensorFlow.js for React Native
            await tf.ready();
            this.isTensorFlowReady = true;
            console.log(' TensorFlow.js ready');

            // Load the model
            await this.loadModel();

            console.log(' ML Inference Service initialized');
        } catch (error) {
            console.error(' Failed to initialize TensorFlow:', error);
            throw error;
        }
    }

    /**
     * Load the ML model from assets
     * 
     * IMPORTANT: The model.tflite file needs to be converted to TensorFlow.js format
     * For now, we'll implement a placeholder that can run mock inference
     */
    private async loadModel(): Promise<void> {
        try {
            console.log(' Loading ML model...');

            // TODO: Convert model.tflite to TensorFlow.js format
            // For production, you need to:
            // 1. Convert model.tflite to SavedModel format
            // 2. Use tensorflowjs_converter to convert to tfjs format
            // 3. Place model.json and weights in assets/ml-model/

            // For now, we'll create a simple placeholder model
            // This will be replaced with actual model loading
            this.model = await this.createPlaceholderModel();

            this.isModelLoaded = true;
            console.log(' Model loaded (placeholder mode)');

            if (ENV.FEATURES.ENABLE_DEBUG_LOGGING) {
                this.model.summary();
            }
        } catch (error) {
            console.error(' Failed to load model:', error);
            throw error;
        }
    }

    /**
     * Create a placeholder model for testing
     * This should be replaced with actual model loading
     */
    private async createPlaceholderModel(): Promise<tf.LayersModel> {
        const model = tf.sequential({
            layers: [
                tf.layers.flatten({ inputShape: [20, 7] }),
                tf.layers.dense({ units: 64, activation: 'relu' }),
                tf.layers.dense({ units: 32, activation: 'relu' }),
                tf.layers.dense({ units: 4, activation: 'softmax' }),
            ],
        });

        model.compile({
            optimizer: 'adam',
            loss: 'categoricalCrossentropy',
            metrics: ['accuracy'],
        });

        return model;
    }

    /**
     * Preprocess sensor data using scaler parameters
     * Standardizes features using mean and std from training
     */
    private preprocessData(sensorMatrix: number[][]): number[][] {
        const { mean, std } = SCALER_PARAMS;

        return sensorMatrix.map((reading) =>
            reading.map((value, idx) => {
                // Standardize: (x - mean) / std
                return (value - mean[idx]) / std[idx];
            })
        );
    }

    /**
     * Run inference on sensor data
     * @param sensorMatrix - 20x7 array of sensor readings
     * @returns Road quality classification (0-3)
     */
    async runInference(sensorMatrix: number[][]): Promise<RoadQuality> {
        if (!this.isModelLoaded) {
            throw new Error('Model not loaded. Call initialize() first');
        }

        try {
            const startTime = Date.now();

            // Preprocess the data
            const preprocessed = this.preprocessData(sensorMatrix);

            // Convert to tensor [1, 20, 7]
            const inputTensor = tf.tensor3d([preprocessed], [1, 20, 7]);

            // Run inference
            const output = this.model!.predict(inputTensor) as tf.Tensor;
            const predictions = await output.data();

            // Get class with highest probability
            const roadQuality = predictions.indexOf(Math.max(...Array.from(predictions))) as RoadQuality;

            // Cleanup tensors
            inputTensor.dispose();
            output.dispose();

            const inferenceTime = Date.now() - startTime;

            if (ENV.FEATURES.ENABLE_DEBUG_LOGGING) {
                console.log(` Inference completed in ${inferenceTime}ms: Quality=${roadQuality}`);
            }

            return roadQuality;
        } catch (error) {
            console.error(' Inference failed:', error);
            throw error;
        }
    }

    /**
     * Run mock inference (for testing without real model)
     * Returns random road quality with weighted probabilities
     */
    async runMockInference(sensorMatrix: number[][]): Promise<RoadQuality> {
        // Simulate inference delay
        await new Promise((resolve) => setTimeout(resolve, 50));

        // Calculate average acceleration magnitude as a simple heuristic
        const avgAccelMagnitude =
            sensorMatrix.reduce((sum, reading) => {
                const [ax, ay, az] = reading;
                return sum + Math.sqrt(ax * ax + ay * ay + az * az);
            }, 0) / sensorMatrix.length;

        // Map acceleration to road quality
        // Higher vibration = worse road quality
        if (avgAccelMagnitude > 12) return 0; // Very bad
        if (avgAccelMagnitude > 11) return 1; // Bad
        if (avgAccelMagnitude > 10) return 2; // Good
        return 3; // Very good

        // Alternatively, return random quality
        // return Math.floor(Math.random() * 4) as RoadQuality;
    }

    /**
     * Check if service is ready
     */
    isReady(): boolean {
        return this.isTensorFlowReady && this.isModelLoaded;
    }

    /**
     * Cleanup resources
     */
    dispose(): void {
        if (this.model) {
            this.model.dispose();
            this.model = null;
        }
        this.isModelLoaded = false;
        console.log(' TFLite Service disposed');
    }
}

// Export singleton instance
export const tfliteService = new TFLiteService();
