/**
 * Windowing Service
 * 
 * Manages 2-second sliding windows of sensor data for ML inference
 * - Window size: 20 readings (2 seconds @ 10 Hz)
 * - Outputs complete windows ready for inference
 */

const WINDOW_SIZE = 20; // 20 readings = 2 seconds at 10 Hz

class WindowManager {
    constructor() {
        this.buffer = [];
        this.onWindowReadyCallback = null;
    }

    /**
     * Initialize the window manager
     * @param {Function} onWindowReady - Callback when a complete window is ready
     */
    initialize(onWindowReady) {
        this.onWindowReadyCallback = onWindowReady;
        this.buffer = [];
        console.log(' Window manager ready (20 readings @ 10Hz)');
    }

    /**
     * Add a new sensor reading to the buffer
     * @param {Object} reading - Sensor reading object
     */
    addReading(reading) {
        // Add reading to buffer
        this.buffer.push(reading);

        // Check if we have a complete window
        if (this.buffer.length >= WINDOW_SIZE) {
            // Extract the first 20 readings as a window
            const window = this.buffer.slice(0, WINDOW_SIZE);

            // Create window metadata
            const windowData = this.createWindowData(window);

            // Remove the oldest reading (sliding window)
            this.buffer.shift();

            // Notify that window is ready
            if (this.onWindowReadyCallback) {
                console.log(' Window complete (20 readings)');
                this.onWindowReadyCallback(windowData);
            }
        }
    }

    /**
     * Create structured window data for ML inference
     * @param {Array} window - Array of 20 sensor readings
     */
    createWindowData(window) {
        // Extract sensor values into a 2D array [20 x 7]
        const sensorMatrix = window.map((reading) => [
            reading.ax,
            reading.ay,
            reading.az,
            reading.wx,
            reading.wy,
            reading.wz,
            reading.speed,
        ]);

        // Calculate metadata from the window
        const speeds = window.map((r) => r.speed);
        const avgSpeed = speeds.reduce((sum, s) => sum + s, 0) / speeds.length;

        // Get the last location (end of window)
        const lastReading = window[window.length - 1];
        const endLocation = lastReading.location;

        return {
            // The 20x7 sensor matrix for ML inference
            sensorMatrix,

            // Metadata for API submission
            metadata: {
                latitude: endLocation.latitude,
                longitude: endLocation.longitude,
                averageSpeed: avgSpeed,
                timestamp: new Date().toISOString(),
                windowStartTime: window[0].timestamp,
                windowEndTime: lastReading.timestamp,
            },
        };
    }

    /**
     * Reset the buffer
     */
    reset() {
        this.buffer = [];

    }

    /**
     * Get current buffer size
     */
    getBufferSize() {
        return this.buffer.length;
    }

    /**
     * Check if buffer is ready for a window
     */
    isReady() {
        return this.buffer.length >= WINDOW_SIZE;
    }
}

// Export singleton instance
export const windowManager = new WindowManager();
