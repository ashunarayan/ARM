/**
 * Shared Type Definitions
 * Centralized types for the entire application
 */

export type RoadQuality = 0 | 1 | 2 | 3;

export interface SensorReading {
    timestamp: number;
    ax: number; // Accelerometer X
    ay: number; // Accelerometer Y
    az: number; // Accelerometer Z
    wx: number; // Gyroscope X
    wy: number; // Gyroscope Y
    wz: number; // Gyroscope Z
    speed: number; // Speed in m/s
}

export interface WindowData {
    sensorMatrix: number[][]; // 20x7 matrix
    metadata: {
        timestamp: number;
        latitude: number;
        longitude: number;
        averageSpeed: number;
        readingCount: number;
    };
}

export interface MLInferenceResult {
    roadQuality: RoadQuality;
    confidence?: number;
    timestamp: number;
    location: {
        latitude: number;
        longitude: number;
    };
    speed: number;
}

export interface RoadSegment {
    id: string;
    startLocation: { latitude: number; longitude: number };
    endLocation: { latitude: number; longitude: number };
    quality: RoadQuality;
    timestamp: number;
}

export interface ObservationPayload {
    latitude: number;
    longitude: number;
    roadQuality: RoadQuality;
    speed: number;
    timestamp: number;
    sessionId?: string;
}

export interface MapLocation {
    latitude: number;
    longitude: number;
    zoom?: number;
}

export interface MapMarker {
    id: string;
    coordinate: [number, number]; // [longitude, latitude] for Mapbox
    quality: RoadQuality;
    timestamp: number;
}
