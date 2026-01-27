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

import { socketService } from './socketService';
import type { MLInferenceResult, ObservationPayload } from '../types';

class ObservationService {
    /**
     * Send a single observation via Socket.IO
     */
    async sendObservation(result: MLInferenceResult): Promise<void> {
        try {
            await socketService.sendRoadQualityUpdate(
                result.roadQuality,
                result.location
            );
            console.log(' Observation sent via Socket.IO');
        } catch (error) {
            console.error(' Failed to send observation:', error);
        }
    }

    /**
     * Legacy queue methods (kept for compatibility but no-op/simplified)
     */
    async sendQueuedObservations(): Promise<void> {}
    setSessionId(sessionId: string): void {}
    getQueueSize(): number { return 0; }
    clearQueue(): void {}
}

// Export singleton instance
export const observationService = new ObservationService();
