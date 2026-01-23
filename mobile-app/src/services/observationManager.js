/**
 * Intelligent Observation Manager
 * 
 * Implements smart observation sending logic to avoid backend spam:
 * - Only sends when road quality changes
 * - OR when distance traveled > 25 meters
 * - OR when minimum time gap (12 seconds) has passed
 * 
 * This ensures efficient data collection while maintaining accuracy for map visualization
 */

/**
 * Calculate distance between two coordinates using Haversine formula
 * @param {number} lat1 - Latitude 1
 * @param {number} lon1 - Longitude 1
 * @param {number} lat2 - Latitude 2
 * @param {number} lon2 - Longitude 2
 * @returns {number} Distance in meters
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Earth radius in meters
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    const Δφ = ((lat2 - lat1) * Math.PI) / 180;
    const Δλ = ((lon2 - lon1) * Math.PI) / 180;

    const a =
        Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
        Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // Distance in meters
}

class ObservationManager {
    constructor() {
        // Tracking state
        this.lastSentObservation = null;
        this.lastSentTimestamp = null;

        // Configurable thresholds
        this.MIN_DISTANCE_METERS = 25; // Send if traveled > 25m
        this.MIN_TIME_SECONDS = 12; // Send if > 12s passed
        this.MAX_TIME_SECONDS = 30; // Force send after 30s regardless

        // Statistics
        this.totalInferences = 0;
        this.totalSent = 0;
        this.skippedDueToDuplicate = 0;
        this.skippedDueToDistance = 0;
        this.skippedDueToTime = 0;
    }

    /**
     * Decide whether to send this observation
     * @param {Object} observation - Current observation {roadQuality, latitude, longitude, speed, timestamp}
     * @returns {boolean} - True if should send, false if should skip
     */
    shouldSendObservation(observation) {
        this.totalInferences++;

        // Always send first observation
        if (!this.lastSentObservation) {
            console.log(' First observation -> SEND');
            return true;
        }

        const currentTime = new Date(observation.timestamp).getTime();
        const timeSinceLastSent = (currentTime - this.lastSentTimestamp) / 1000;

        // Rule 1: Road quality changed
        if (observation.roadQuality !== this.lastSentObservation.roadQuality) {
            console.log(
                ` Quality changed: ${this.lastSentObservation.roadQuality}→${observation.roadQuality} -> SEND`
            );
            return true;
        }

        // Rule 2: Distance threshold
        const distanceTraveled = calculateDistance(
            this.lastSentObservation.latitude,
            this.lastSentObservation.longitude,
            observation.latitude,
            observation.longitude
        );

        if (distanceTraveled >= this.MIN_DISTANCE_METERS) {
            console.log(
                ` Distance: ${distanceTraveled.toFixed(0)}m -> SEND`
            );
            return true;
        }

        // Rule 3: Time threshold (if moving)
        if (timeSinceLastSent >= this.MIN_TIME_SECONDS && observation.speed > 1) {
            console.log(
                ` Time: ${timeSinceLastSent.toFixed(0)}s -> SEND`
            );
            return true;
        }

        // Rule 4: Force send safety net
        if (timeSinceLastSent >= this.MAX_TIME_SECONDS) {
            console.log(
                ` Max time: ${timeSinceLastSent.toFixed(0)}s -> FORCE SEND`
            );
            return true;
        }

        // Skip
        console.log(
            `⏭ SKIP: Q=${observation.roadQuality}, d=${distanceTraveled.toFixed(0)}m, t=${timeSinceLastSent.toFixed(0)}s`
        );
        this.skippedDueToDistance++;

        return false;
    }

    /**
     * Mark observation as sent
     * @param {Object} observation - Sent observation
     */
    markAsSent(observation) {
        this.lastSentObservation = observation;
        this.lastSentTimestamp = new Date(observation.timestamp).getTime();
        this.totalSent++;
    }

    /**
     * Get efficiency statistics
     */
    getStats() {
        const efficiency = this.totalInferences > 0
            ? ((this.totalInferences - this.totalSent) / this.totalInferences * 100).toFixed(1)
            : 0;

        return {
            totalInferences: this.totalInferences,
            totalSent: this.totalSent,
            totalSkipped: this.totalInferences - this.totalSent,
            efficiencyPercent: efficiency,
            breakdown: {
                skippedDueToDuplicate: this.skippedDueToDuplicate,
                skippedDueToDistance: this.skippedDueToDistance,
                skippedDueToTime: this.skippedDueToTime,
            },
        };
    }

    /**
     * Reset statistics
     */
    resetStats() {
        this.totalInferences = 0;
        this.totalSent = 0;
        this.skippedDueToDuplicate = 0;
        this.skippedDueToDistance = 0;
        this.skippedDueToTime = 0;
    }

    /**
     * Reset manager state (e.g., when user stops/starts trip)
     */
    reset() {
        this.lastSentObservation = null;
        this.lastSentTimestamp = null;
    }

    /**
     * Configure thresholds
     */
    configure(options = {}) {
        if (options.minDistanceMeters !== undefined) {
            this.MIN_DISTANCE_METERS = options.minDistanceMeters;
        }
        if (options.minTimeSeconds !== undefined) {
            this.MIN_TIME_SECONDS = options.minTimeSeconds;
        }
        if (options.maxTimeSeconds !== undefined) {
            this.MAX_TIME_SECONDS = options.maxTimeSeconds;
        }
    }
}

// Export singleton instance
export const observationManager = new ObservationManager();
