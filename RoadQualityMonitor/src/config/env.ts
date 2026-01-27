export const ENV = {
    // Backend API configuration
    API: {
        // Replace with your local machine's IP address (e.g., 192.168.1.X) for Android Emulator/Physical Device
        // 'localhost' works for iOS Simulator but not Android Emulator (use 10.0.2.2 usually)
        BASE_URL: 'http://localhost:5000', 
        TIMEOUT: 10000,
    },

    // Mapbox / OSM configuration
    MAP: {
        DEFAULT_CENTER: {
            latitude: 37.7749,
            longitude: -122.4194,
        },
        DEFAULT_ZOOM: 15,
        // OpenStreetMap Tile URL
        TILE_URL: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    },
    
    // Mapbox Public Token (Required for @rnmapbox/maps)
    MAPBOX_TOKEN: 'pk.eyJ1IjoidHVzaGFyYmFzYWsiLCJhIjoiY21rcmE4ZWV4MHdjYzNnczZxMXVyMWFmbiJ9.qMgF1d8iOC4XVP_iQetlPA',

    // ML Model configuration
    ML: {
        // TFLite model loaded via react-native-fast-tflite form bundle/assets
        MODEL_FILE: require('../../assets/ml-model/model.tflite'), 
        SCALER_FILE: require('../../assets/ml-model/scaler_params.json'),
        WINDOW_SIZE: 20, 
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
