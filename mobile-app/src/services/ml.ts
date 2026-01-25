/**
 * ML Service - High-level orchestrator for road quality detection
 * 
 * ARCHITECTURE:
 * - Coordinates sensor data collection, windowing, and inference
 * - Provides simple API for starting/stopping monitoring
 * - Returns results with location metadata
 * - Isolated from UI and API logic
 * - Results can be consumed by observation service or UI
 * 
 * WORKFLOW:
 * 1. Sensor data collected at 10Hz
 * 2. Readings buffered into 2-second windows (20 readings)
 * 3. Inference runs on each complete window
 * 4. Results stored with location metadata
 * 5. Can be sent to backend or displayed on map
 */

import { sensorCollector } from './sensorService';
import { windowManager } from './windowService';
import { tfliteService } from './tflite';
import type { MLInferenceResult, WindowData, RoadQuality } from '../types';
import { ROAD_QUALITY_LABELS } from '../config/env';

export type MLResultCallback = (result: MLInferenceResult) => void;

class MLService {
    private isInitialized = false;
    private isCollecting = false;
    private latestResult: MLInferenceResult | null = null;
    private pendingInference = false;
    private resultCallbacks: MLResultCallback[] = [];

    /**
     * Initialize the ML service
     * MUST be called once when app starts (before using any ML features)
     */
    async initialize(): Promise<void> {
        if (this.isInitialized) {
            console.log(' ML Service already initialized');
            return;
        }

        try {
            console.log(' Initializing ML Service...');

            // Check sensor availability
            await sensorCollector.checkSensorAvailability();

            // Initialize TensorFlow and load model
            await tfliteService.initialize();

            this.isInitialized = true;
            console.log(' ML Service initialized successfully');
        } catch (error) {
            console.error(' ML Service initialization failed:', error);
            throw error;
        }
    }

    /**
     * Start continuous road quality monitoring
     * Collects sensor data and runs inference every 2 seconds
     * 
     * @param onResult - Optional callback for each inference result
     */
    async startMonitoring(onResult?: MLResultCallback): Promise<void> {
        if (!this.isInitialized) {
            throw new Error('ML Service not initialized. Call initialize() first');
        }

        if (this.isCollecting) {
            console.log(' ML monitoring already running');
            return;
        }

        if (onResult) {
            this.resultCallbacks.push(onResult);
        }

        console.log(' Starting ML monitoring (10Hz sensors, 2s windows)');
        this.isCollecting = true;

        // Initialize window manager with callback
        windowManager.initialize(async (windowData: WindowData) => {
            await this.processWindow(windowData);
        });

        // Start collecting sensor data
        await sensorCollector.startCollecting((reading: any) => {
            windowManager.addReading(reading);
        });
    }

    /**
     * Stop road quality monitoring
     */
    stopMonitoring(): void {
        if (!this.isCollecting) return;

        console.log(' Stopping ML monitoring');
        this.isCollecting = false;

        sensorCollector.stopCollecting();
        windowManager.reset();
        this.resultCallbacks = [];
    }

    /**
     * Process a complete 2-second window
     * Runs inference and stores result
     */
    private async processWindow(windowData: WindowData): Promise<void> {
        if (this.pendingInference) {
            return; // Skip if previous inference still running
        }

        try {
            this.pendingInference = true;

            // Run inference
            let roadQuality: RoadQuality;
            if (tfliteService.isReady()) {
                roadQuality = await tfliteService.runInference(windowData.sensorMatrix);
            } else {
                console.log(' Model not ready, using mock inference');
                roadQuality = await tfliteService.runMockInference(windowData.sensorMatrix);
            }

            // Create result with metadata
            const result: MLInferenceResult = {
                roadQuality,
                timestamp: windowData.metadata.timestamp,
                location: {
                    latitude: windowData.metadata.latitude,
                    longitude: windowData.metadata.longitude,
                },
                speed: windowData.metadata.averageSpeed,
            };

            this.latestResult = result;

            // Notify callbacks
            this.resultCallbacks.forEach((callback) => {
                try {
                    callback(result);
                } catch (error) {
                    console.error(' Result callback error:', error);
                }
            });

            console.log(
                ` Quality: ${ROAD_QUALITY_LABELS[roadQuality]} (${roadQuality}) at [${result.location.latitude.toFixed(4)}, ${result.location.longitude.toFixed(4)}]`
            );
        } catch (error) {
            console.error(' Inference failed:', error);
        } finally {
            this.pendingInference = false;
        }
    }

    /**
     * Get the latest road quality result
     * Returns null if no result available yet
     */
    getLatestResult(): MLInferenceResult | null {
        return this.latestResult;
    }

    /**
     * Add a result callback
     * Callback will be called for each new inference result
     */
    onResult(callback: MLResultCallback): void {
        if (!this.resultCallbacks.includes(callback)) {
            this.resultCallbacks.push(callback);
        }
    }

    /**
     * Remove a result callback
     */
    offResult(callback: MLResultCallback): void {
        this.resultCallbacks = this.resultCallbacks.filter((cb) => cb !== callback);
    }

    /**
     * Check if service is ready to collect data
     */
    isReady(): boolean {
        return this.isInitialized && tfliteService.isReady();
    }

    /**
     * Check if currently monitoring
     */
    isMonitoring(): boolean {
        return this.isCollecting;
    }

    /**
     * Cleanup resources
     */
    dispose(): void {
        this.stopMonitoring();
        tfliteService.dispose();
        this.isInitialized = false;
        this.latestResult = null;
        this.resultCallbacks = [];
        console.log(' ML Service disposed');
    }
}

// Export singleton instance
export const mlService = new MLService();
