/**
 * ML Service - High-level API for road quality detection
 * 
 * Orchestrates the complete ML pipeline:
 * 1. Sensor data collection
 * 2. Windowing (2-second buffers)
 * 3. TFLite inference
 * 4. Result delivery
 */

import { sensorCollector } from './sensorService';
import { windowManager } from './windowService';
import { tfliteService } from './tfliteService';

class MLService {
  constructor() {
    this.isInitialized = false;
    this.isCollecting = false;
    this.latestResult = null;
    this.pendingInference = false;
  }

  /**
   * Initialize the ML service
   * Must be called once when app starts
   */
  async initialize() {
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
   */
  async startMonitoring() {
    if (!this.isInitialized) {
      throw new Error('ML Service not initialized. Call initialize() first');
    }

    if (this.isCollecting) {
      return;
    }

    console.log(' Starting ML monitoring (10Hz sensors, 2s windows)');
    this.isCollecting = true;

    // Initialize window manager with callback
    windowManager.initialize(async (windowData) => {
      await this.processWindow(windowData);
    });

    // Start collecting sensor data
    await sensorCollector.startCollecting((reading) => {
      windowManager.addReading(reading);
    });
  }

  /**
   * Stop road quality monitoring
   */
  stopMonitoring() {
    if (!this.isCollecting) return;

    console.log(' Stopping ML monitoring');
    this.isCollecting = false;

    sensorCollector.stopCollecting();
    windowManager.reset();
  }

  /**
   * Process a complete 2-second window
   * @param {Object} windowData - Complete window with sensor matrix and metadata
   */
  async processWindow(windowData) {
    if (this.pendingInference) {
      return;
    }

    try {
      this.pendingInference = true;

      // Run inference
      let roadQuality;
      if (tfliteService.isReady()) {
        roadQuality = await tfliteService.runInference(windowData.sensorMatrix);
      } else {
        console.log(' Model not ready, using mock inference');
        roadQuality = await tfliteService.runMockInference(windowData.sensorMatrix);
      }

      // Store the result with metadata
      this.latestResult = {
        roadQuality,
        latitude: windowData.metadata.latitude,
        longitude: windowData.metadata.longitude,
        speed: windowData.metadata.averageSpeed,
        timestamp: windowData.metadata.timestamp,
      };

      console.log(` Inference: Quality=${roadQuality} (${this.getRoadQualityLabel(roadQuality)})`);
    } catch (error) {
      console.error(' Inference failed:', error.message);
    } finally {
      this.pendingInference = false;
    }
  }

  /**
   * Get the latest road quality result
   * Used by observationService to send data to backend
   * 
   * @returns {Object} Latest result with roadQuality and metadata
   */
  getLatestResult() {
    if (!this.latestResult) {
      console.log(' No road quality result available yet');
      return null;
    }

    return this.latestResult;
  }

  /**
   * Get road quality label from numeric value
   */
  getRoadQualityLabel(value) {
    const labels = {
      0: 'very bad',
      1: 'bad',
      2: 'good',
      3: 'very good',
    };
    return labels[value] || 'unknown';
  }

  /**
   * Check if service is ready to collect data
   */
  isReady() {
    return this.isInitialized && tfliteService.isReady();
  }

  /**
   * Cleanup resources
   */
  dispose() {
    this.stopMonitoring();
    tfliteService.dispose();
    this.isInitialized = false;
    console.log(' ML Service disposed');
  }
}

// Export singleton instance
export const mlService = new MLService();

/**
 * Legacy function for backward compatibility
 * Returns just the road quality value
 */
export const getRoadQualityFromML = async () => {
  const result = mlService.getLatestResult();

  if (!result) {
    console.log(' No ML result available, returning default');
    return 2; // Default to 'good'
  }

  return result.roadQuality;
};
