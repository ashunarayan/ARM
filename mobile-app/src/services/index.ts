/**
 * Services Index
 * Centralized export of all services for clean imports
 * 
 * USAGE:
 * import { mlService, mapboxService, observationService } from './services';
 */

// Core services
export { mapboxService } from './mapboxService';
export { mlService } from './ml';
export { tfliteService } from './tflite';
export { observationService } from './observation';
export { initializeApp, appInitializer } from './appInitializer';

// API client
export { apiRequest, setAuthToken, getAuthToken } from '../api/client';

// Legacy services (keep for now)
export { sensorCollector } from './sensorService';
export { windowManager } from './windowService';
export { initAuth } from './auth';

// Re-export types for convenience
export type {
    RoadQuality,
    SensorReading,
    WindowData,
    MLInferenceResult,
    RoadSegment,
    ObservationPayload,
    MapLocation,
    MapMarker,
} from '../types';
