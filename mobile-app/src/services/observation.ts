/**
 * Observation Service
 * Handles sending road quality observations to backend
 * 
 * ARCHITECTURE:
 * - Consumes ML inference results
 * - Sends observations to backend API
 * - Batching and retry logic
 * - Isolated from UI and ML logic
 * 
 * USAGE:
 * const result = mlService.getLatestResult();
 * await observationService.sendObservation(result);
 */

import { apiRequest } from '../api/client';
import type { MLInferenceResult, ObservationPayload } from '../types';

class ObservationService {
    private sessionId: string | null = null;
    private observationQueue: ObservationPayload[] = [];
    private isSending = false;

    /**
     * Set the current session ID
     */
    setSessionId(sessionId: string): void {
        this.sessionId = sessionId;
    }

    /**
     * Send a single observation to the backend
     */
    async sendObservation(result: MLInferenceResult): Promise<void> {
        try {
            const payload: ObservationPayload = {
                latitude: result.location.latitude,
                longitude: result.location.longitude,
                roadQuality: result.roadQuality,
                speed: result.speed,
                timestamp: new Date(result.timestamp).toISOString(),
                sessionId: this.sessionId || undefined,
            };

            await apiRequest('/observations', {
                method: 'POST',
                body: payload,
            });

            console.log(' Observation sent successfully');
        } catch (error) {
            console.error(' Failed to send observation:', error);

            // Queue for retry
            this.queueObservation({
                latitude: result.location.latitude,
                longitude: result.location.longitude,
                roadQuality: result.roadQuality,
                speed: result.speed,
                timestamp: new Date(result.timestamp).toISOString(),
                sessionId: this.sessionId || undefined,
            });
        }
    }

    /**
     * Queue an observation for later sending
     */
    private queueObservation(payload: ObservationPayload): void {
        this.observationQueue.push(payload);
        console.log(` Observation queued (${this.observationQueue.length} in queue)`);
    }

    /**
     * Send all queued observations
     */
    async sendQueuedObservations(): Promise<void> {
        if (this.isSending || this.observationQueue.length === 0) {
            return;
        }

        this.isSending = true;

        try {
            const batch = [...this.observationQueue];
            this.observationQueue = [];

            for (const payload of batch) {
                try {
                    await apiRequest('/observations', {
                        method: 'POST',
                        body: payload,
                    });
                } catch (error) {
                    console.error(' Failed to send queued observation:', error);
                    // Re-queue failed observation
                    this.observationQueue.push(payload);
                }
            }

            console.log(' Queued observations sent');
        } finally {
            this.isSending = false;
        }
    }

    /**
     * Get the number of queued observations
     */
    getQueueSize(): number {
        return this.observationQueue.length;
    }

    /**
     * Clear all queued observations
     */
    clearQueue(): void {
        this.observationQueue = [];
    }
}

// Export singleton instance
export const observationService = new ObservationService();
