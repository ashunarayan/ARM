export interface Observation {
    latitude: number;
    longitude: number;
    roadQuality: 0 | 1 | 2 | 3;
    timestamp: string;
    speed?: number;
    deviceMetadata?: {
        model: string;
        os: string;
        appVersion: string;
    };
}

export interface RoadSegment {
    roadSegmentId: string;
    aggregatedQualityScore: number;
    confidenceScore: number;
    geometry: {
        type: 'LineString';
        coordinates: number[][];
    };
    regionId: string;
}

export interface User {
    uid: string;
    email: string;
    displayName?: string;
}

export interface SensorReading {
    ax: number;
    ay: number;
    az: number;
    wx: number;
    wy: number;
    wz: number;
    speed: number;
}

export interface MLInput {
    readings: SensorReading[];
}
