/**
 * App Initialization Service
 * Centralized initialization for all services
 * 
 * ARCHITECTURE:
 * - Initializes all services in correct order
 * - Handles initialization errors
 * - Should be called once at app startup
 * - Call from _layout.tsx
 * 
 * INITIALIZATION ORDER:
 * 1. Mapbox (required before any map components render)
 * 2. ML Service (TensorFlow + model loading)
 * 
 * USAGE:
 * await initializeApp();
 */

import { mapboxService } from './mapboxService';
import { mlService } from './ml';

export interface InitializationStatus {
    mapbox: boolean;
    ml: boolean;
    errors: string[];
}

class AppInitializer {
    private isInitialized = false;
    private status: InitializationStatus = {
        mapbox: false,
        ml: false,
        errors: [],
    };

    /**
     * Initialize all app services
     * MUST be called once at app startup
     */
    async initialize(): Promise<InitializationStatus> {
        if (this.isInitialized) {
            console.log(' App already initialized');
            return this.status;
        }

        console.log(' Starting app initialization...');

        // Reset status
        this.status = {
            mapbox: false,
            ml: false,
            errors: [],
        };

        // Initialize Mapbox
        try {
            await mapboxService.initialize();
            this.status.mapbox = true;
            console.log(' Mapbox initialized');
        } catch (error) {
            const errorMsg = `Mapbox initialization failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
            this.status.errors.push(errorMsg);
            console.error('', errorMsg);
        }

        // Initialize ML Service
        try {
            await mlService.initialize();
            this.status.ml = true;
            console.log(' ML Service initialized');
        } catch (error) {
            const errorMsg = `ML Service initialization failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
            this.status.errors.push(errorMsg);
            console.error('', errorMsg);
        }

        this.isInitialized = this.status.mapbox && this.status.ml;

        if (this.isInitialized) {
            console.log(' App initialization complete!');
        } else {
            console.warn('  App initialization completed with errors:', this.status.errors);
        }

        return this.status;
    }

    /**
     * Get initialization status
     */
    getStatus(): InitializationStatus {
        return { ...this.status };
    }

    /**
     * Check if app is fully initialized
     */
    isReady(): boolean {
        return this.isInitialized;
    }

    /**
     * Reset initialization state (useful for testing)
     */
    reset(): void {
        this.isInitialized = false;
        this.status = {
            mapbox: false,
            ml: false,
            errors: [],
        };
    }
}

// Export singleton instance
export const appInitializer = new AppInitializer();

/**
 * Convenience function for app initialization
 */
export const initializeApp = async (): Promise<InitializationStatus> => {
    return await appInitializer.initialize();
};
