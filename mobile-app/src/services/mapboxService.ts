/**
 * Mapbox Service
 * Handles Mapbox initialization and configuration
 * 
 * ARCHITECTURE:
 * - Initializes Mapbox once at app startup
 * - Provides utilities for location and map operations
 * - Isolated from ML and API logic
 * - Used by MapView component
 */

import Mapbox from '@rnmapbox/maps';
import { ENV } from '../config/env';
import type { MapLocation } from '../types';

class MapboxService {
    private isInitialized = false;

    /**
     * Initialize Mapbox with access token
     * MUST be called once at app startup (before any map components render)
     */
    async initialize(): Promise<void> {
        if (this.isInitialized) {
            console.log('  Mapbox already initialized');
            return;
        }

        try {
            console.log('  Initializing Mapbox...');

            // Set Mapbox access token from environment
            Mapbox.setAccessToken(ENV.MAPBOX.ACCESS_TOKEN);

            // Optional: Set telemetry (for production, you might want to disable)
            Mapbox.setTelemetryEnabled(false);

            this.isInitialized = true;
            console.log('  Mapbox initialized successfully');
        } catch (error) {
            console.error('  Failed to initialize Mapbox:', error);
            throw error;
        }
    }

    /**
     * Check if Mapbox is initialized
     */
    isReady(): boolean {
        return this.isInitialized;
    }

    /**
     * Convert latitude/longitude to Mapbox coordinate format [lng, lat]
     */
    toMapboxCoordinate(latitude: number, longitude: number): [number, number] {
        return [longitude, latitude];
    }

    /**
     * Convert Mapbox coordinate [lng, lat] to latitude/longitude
     */
    fromMapboxCoordinate(coordinate: [number, number]): { latitude: number; longitude: number } {
        return {
            latitude: coordinate[1],
            longitude: coordinate[0],
        };
    }

    /**
     * Get default map location
     */
    getDefaultLocation(): MapLocation {
        return {
            latitude: ENV.MAPBOX.DEFAULT_CENTER.latitude,
            longitude: ENV.MAPBOX.DEFAULT_CENTER.longitude,
            zoom: ENV.MAPBOX.DEFAULT_ZOOM,
        };
    }
}

// Export singleton instance
export const mapboxService = new MapboxService();
