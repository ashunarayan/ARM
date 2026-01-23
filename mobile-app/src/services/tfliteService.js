/**
 * TensorFlow Lite Inference Service
 * 
 * Loads the TFLite model and runs on-device inference
 * - Model: Hybrid CNN for road quality classification
 * - Input: 20x7 sensor matrix (2-second window)
 * - Output: Integer classification (0-3)
 */

import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-react-native';
import * as FileSystem from 'expo-file-system';
import { Asset } from 'expo-asset';
import { bundleResourceIO } from '@tensorflow/tfjs-react-native';

class TFLiteInferenceService {
    constructor() {
        this.model = null;
        this.isModelLoaded = false;
        this.isTensorFlowReady = false;
    }

    /**
     * Initialize TensorFlow.js and load the model
     */
    async initialize() {
        try {
            console.log(' Initializing TensorFlow.js...');

            // Initialize TensorFlow.js for React Native
            await tf.ready();
            this.isTensorFlowReady = true;
            console.log(' TensorFlow.js ready');

            // Load the TFLite model
            await this.loadModel();

            console.log(' ML Inference Service initialized');
        } catch (error) {
            console.error(' Failed to initialize TensorFlow:', error);
            throw error;
        }
    }

    /**
     * Load the TFLite model from assets
     */
    async loadModel() {
        try {
            console.log(' Loading ML model...');

            // Method 1: Using bundleResourceIO (recommended for Expo)
            try {
                const modelJson = require('../../assets/ml-model/model.json');
                const modelWeights = require('../../assets/ml-model/weights.bin');

                this.model = await tf.loadLayersModel(
                    bundleResourceIO(modelJson, modelWeights)
                );
            } catch (e) {
                // Method 2: If TFLite model is directly available
                // Note: You may need to convert .tflite to TensorFlow.js format
                console.log(' Using alternative model loading method');

                // For actual TFLite file, you would need to:
                // 1. Convert model.tflite to tfjs format using tensorflowjs_converter
                // 2. Place model.json and weights in assets/ml-model/
                throw new Error('Model not found. Please convert model.tflite to TensorFlow.js format');
            }

            this.isModelLoaded = true;
            console.log(' Model loaded successfully');

            // Log model summary
            this.model.summary();
        } catch (error) {
            console.error(' Failed to load model:', error);
            throw error;
        }
    }

    /**
     * Run inference on a sensor data window
     * @param {Array} sensorMatrix - 20x7 array of sensor readings
     * @returns {number} - Road quality classification (0-3)
     */
    async runInference(sensorMatrix) {
        if (!this.isModelLoaded) {
            console.error(' Model not loaded. Call initialize() first');
            throw new Error('Model not loaded');
        }

        try {
            console.log(' Running inference...');
            const startTime = Date.now();

            // Convert sensor matrix to tensor
            // Shape: [1, 20, 7] - batch size 1, 20 time steps, 7 features
            const inputTensor = tf.tensor3d([sensorMatrix], [1, 20, 7]);

            // Run prediction
            const prediction = this.model.predict(inputTensor);

            // Get the predicted class
            const predictionData = await prediction.data();
            const predictedClass = prediction.argMax(-1).dataSync()[0];

            // Clean up tensors
            inputTensor.dispose();
            prediction.dispose();

            const inferenceTime = Date.now() - startTime;
            console.log(` Inference complete in ${inferenceTime}ms`);
            console.log(` Predicted road quality: ${predictedClass}`);
            console.log(` Confidence scores:`, Array.from(predictionData));

            // Return the predicted road quality (0-3)
            return predictedClass;
        } catch (error) {
            console.error(' Inference failed:', error);
            throw error;
        }
    }

    /**
     * Alternative inference method using mock/fallback
     * Use this temporarily while converting the TFLite model
     */
    async runMockInference(sensorMatrix) {
        console.log(' Using MOCK inference (model not yet loaded)');

        // Simulate processing time
        await new Promise(resolve => setTimeout(resolve, 50));

        // Calculate a simple heuristic based on accelerometer magnitude
        // This is just a placeholder until real model is loaded
        const avgAccelMagnitude = sensorMatrix.reduce((sum, reading) => {
            const mag = Math.sqrt(reading[0] ** 2 + reading[1] ** 2 + reading[2] ** 2);
            return sum + mag;
        }, 0) / sensorMatrix.length;

        // Mock classification based on acceleration
        if (avgAccelMagnitude > 15) return 0; // very bad
        if (avgAccelMagnitude > 12) return 1; // bad
        if (avgAccelMagnitude > 10) return 2; // good
        return 3; // very good
    }

    /**
     * Check if the service is ready
     */
    isReady() {
        return this.isTensorFlowReady && this.isModelLoaded;
    }

    /**
     * Cleanup resources
     */
    dispose() {
        if (this.model) {
            this.model.dispose();
            this.model = null;
            this.isModelLoaded = false;
        }
        console.log(' Model disposed');
    }
}

// Export singleton instance
export const tfliteService = new TFLiteInferenceService();
