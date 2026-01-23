/**
 * Sensor Data Collection Service
 * 
 * Collects accelerometer, gyroscope, and location data for ML inference
 * Sampling rate: 10 Hz (100ms intervals)
 */

import { Accelerometer, Gyroscope } from 'expo-sensors';
import * as Location from 'expo-location';

const SAMPLING_INTERVAL_MS = 100; // 10 Hz = 100ms per sample

class SensorCollector {
    constructor() {
        this.isCollecting = false;
        this.accelerometerSubscription = null;
        this.gyroscopeSubscription = null;
        this.locationSubscription = null;

        // Current sensor readings
        this.currentAccel = { x: 0, y: 0, z: 0 };
        this.currentGyro = { x: 0, y: 0, z: 0 };
        this.currentSpeed = 0;
        this.currentLocation = { latitude: 0, longitude: 0 };

        // Callbacks
        this.onDataCallback = null;
    }

    /**
     * Start collecting sensor data
     * @param {Function} onData - Callback function that receives sensor readings
     */
    async startCollecting(onData) {
        if (this.isCollecting) {
            console.log(' Sensor collection already active');
            return;
        }

        console.log(' Starting sensor collection at 10 Hz');
        this.onDataCallback = onData;
        this.isCollecting = true;

        // Request location permissions
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
            throw new Error('Location permission denied');
        }

        // Set sensor update intervals to 100ms (10 Hz)
        Accelerometer.setUpdateInterval(SAMPLING_INTERVAL_MS);
        Gyroscope.setUpdateInterval(SAMPLING_INTERVAL_MS);

        // Subscribe to accelerometer
        this.accelerometerSubscription = Accelerometer.addListener((data) => {
            this.currentAccel = {
                x: data.x,
                y: data.y,
                z: data.z,
            };
        });

        // Subscribe to gyroscope
        this.gyroscopeSubscription = Gyroscope.addListener((data) => {
            this.currentGyro = {
                x: data.x,
                y: data.y,
                z: data.z,
            };
        });

        // Subscribe to location updates
        this.locationSubscription = await Location.watchPositionAsync(
            {
                accuracy: Location.Accuracy.High,
                timeInterval: SAMPLING_INTERVAL_MS,
                distanceInterval: 0, // Update on every change
            },
            (location) => {
                this.currentLocation = {
                    latitude: location.coords.latitude,
                    longitude: location.coords.longitude,
                };
                this.currentSpeed = location.coords.speed || 0;
            }
        );

        // Start the sampling timer
        this.startSampling();
    }

    /**
     * Start periodic sampling at 10 Hz
     */
    startSampling() {
        this.samplingInterval = setInterval(() => {
            if (!this.isCollecting) return;

            // Create a complete sensor reading
            const reading = {
                ax: this.currentAccel.x,
                ay: this.currentAccel.y,
                az: this.currentAccel.z,
                wx: this.currentGyro.x,
                wy: this.currentGyro.y,
                wz: this.currentGyro.z,
                speed: this.currentSpeed,
                timestamp: Date.now(),
                location: {
                    latitude: this.currentLocation.latitude,
                    longitude: this.currentLocation.longitude,
                },
            };

            // Send reading to callback
            if (this.onDataCallback) {
                this.onDataCallback(reading);
            }
        }, SAMPLING_INTERVAL_MS);
    }

    /**
     * Stop collecting sensor data
     */
    stopCollecting() {
        if (!this.isCollecting) return;

        console.log(' Stopping sensor collection');
        this.isCollecting = false;

        // Clear sampling interval
        if (this.samplingInterval) {
            clearInterval(this.samplingInterval);
            this.samplingInterval = null;
        }

        // Unsubscribe from sensors
        if (this.accelerometerSubscription) {
            this.accelerometerSubscription.remove();
            this.accelerometerSubscription = null;
        }

        if (this.gyroscopeSubscription) {
            this.gyroscopeSubscription.remove();
            this.gyroscopeSubscription = null;
        }

        if (this.locationSubscription) {
            this.locationSubscription.remove();
            this.locationSubscription = null;
        }

        this.onDataCallback = null;
    }

    /**
     * Check if sensors are available on device
     */
    async checkSensorAvailability() {
        const accelAvailable = await Accelerometer.isAvailableAsync();
        const gyroAvailable = await Gyroscope.isAvailableAsync();

        if (!accelAvailable) {
            throw new Error('Accelerometer not available on this device');
        }

        if (!gyroAvailable) {
            throw new Error('Gyroscope not available on this device');
        }

        console.log(' All sensors available');
        return true;
    }
}

// Export singleton instance
export const sensorCollector = new SensorCollector();
