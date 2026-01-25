/**
 * Environment Configuration
 * Centralizes all environment variables and configuration
 * 
 * IMPORTANT: Never hardcode sensitive values here
 */

// Load environment variables
// In production, use expo-constants or expo-env
const MAPBOX_ACCESS_TOKEN = process.env.MAPBOX_ACCESS_TOKEN || 'pk.eyJ1IjoiYXNodS1zcmkiLCJhIjoiY21rdG9mNjM0MXFpZTNscW5tdGhhN212aCJ9.ODYbCtFkoMBaKakX-3sHWw';
const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://10.66.175.173:5000/api';

export const ENV = {
    // Mapbox configuration
    MAPBOX: {
        ACCESS_TOKEN: MAPBOX_ACCESS_TOKEN,
        DEFAULT_CENTER: {
            latitude: 37.7749,
            longitude: -122.4194,
        },
        DEFAULT_ZOOM: 12,
    },

    // Backend API configuration
    API: {
        BASE_URL: BACKEND_BASE_URL,
        TIMEOUT: 10000, // 10 seconds
    },

    // ML Model configuration
    ML: {
        MODEL_PATH: require('../../assets/ml-model/model.tflite'),
        SCALER_PARAMS_PATH: require('../../assets/ml-model/scaler_params.json'),
        SENSOR_FREQUENCY: 10, // Hz
        WINDOW_DURATION: 2, // seconds
        WINDOW_SIZE: 20, // readings per window
        FEATURE_COUNT: 7, // ax, ay, az, wx, wy, wz, speed
    },

    // Feature flags
    FEATURES: {
        ENABLE_MOCK_INFERENCE: false,
        ENABLE_DEBUG_LOGGING: __DEV__,
    },
} as const;

export type RoadQuality = 0 | 1 | 2 | 3;

export const ROAD_QUALITY_LABELS: Record<RoadQuality, string> = {
    0: 'Very Bad',
    1: 'Bad',
    2: 'Good',
    3: 'Very Good',
};

export const ROAD_QUALITY_COLORS: Record<RoadQuality, string> = {
    0: '#FF0000', // Red
    1: '#FF8C00', // Orange
    2: '#FFD700', // Yellow
    3: '#00FF00', // Green
};
