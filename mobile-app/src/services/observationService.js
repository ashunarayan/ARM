/**
 * Observation Service
 *
 * Sends road quality observations to the backend API
 * Uses data from the ML pipeline (sensor → window → inference)
 *
 * INTELLIGENT SENDING:
 * - Only sends when road quality changes
 * - OR when distance > 25m traveled
 * - OR when time > 12s elapsed
 *
 * Prevents backend spam while keeping map-ready data
 */

import { apiRequest } from "../api/client";
import { mlService } from "./mlService";
import { observationManager } from "./observationManager";

/**
 * Send a road quality observation to the backend
 *
 * IMPORTANT:
 * Sends ONLY backend-compatible fields
 * - latitude, longitude, roadQuality, speed, timestamp
 *
 * @param {boolean} force
 */
export const sendObservation = async (force = false) => {
  try {
    const result = mlService.getLatestResult();

    if (!result) {
      return { sent: false, reason: "no_result" };
    }

    if (!force && !observationManager.shouldSendObservation(result)) {
      return { sent: false, reason: "filtered" };
    }

    // Backend API contract: ONLY these 5 fields
    const payload = {
      latitude: result.latitude,
      longitude: result.longitude,
      roadQuality: result.roadQuality,  // 0-3 from ML model
      speed: result.speed,
      timestamp: result.timestamp,  // ISO-8601 format
    };

    console.log(" Sending observation:", {
      quality: mlService.getRoadQualityLabel(result.roadQuality),
      lat: payload.latitude.toFixed(6),
      lng: payload.longitude.toFixed(6),
      speed: payload.speed.toFixed(1)
    });

    await apiRequest("/observations", "POST", payload);

    observationManager.markAsSent(result);

    console.log(" Observation saved to backend");
    return { sent: true };
  } catch (error) {
    console.error(" Observation failed:", error.message);
    throw error;
  }
};

/**
 * Start continuous observation collection
 */
export const startObservationCollection = async (options = {}) => {
  try {
    const {
      checkIntervalSeconds = 2,
      minDistanceMeters = 25,
      minTimeSeconds = 12,
      maxTimeSeconds = 30,
    } = options;

    console.log(" Starting intelligent observation collection");
    console.log(`   Distance threshold: ${minDistanceMeters}m | Time threshold: ${minTimeSeconds}s`);

    observationManager.configure({
      minDistanceMeters,
      minTimeSeconds,
      maxTimeSeconds,
    });

    if (!mlService.isReady()) {
      console.log(" Initializing ML Service...");
      await mlService.initialize();
    }

    await mlService.startMonitoring();
    observationManager.reset();

    const intervalMs = checkIntervalSeconds * 1000;

    const observationInterval = setInterval(async () => {
      try {
        await sendObservation();
      } catch (error) {
        console.error(" Observation failed:", error.message);
      }
    }, intervalMs);

    console.log(" Collection started - ML runs every 2s, sends intelligently");

    // Cleanup function
    return () => {
      clearInterval(observationInterval);
      mlService.stopMonitoring();
      observationManager.reset();

      const stats = observationManager.getStats();
      console.log(" Collection Statistics:", stats);
      console.log(" Observation collection stopped");
    };
  } catch (error) {
    console.error(" Failed to start observation collection:", error);
    throw error;
  }
};

/**
 * Get current collection statistics
 */
export const getCollectionStats = () => {
  return observationManager.getStats();
};

/**
 * Reset observation manager (new trip)
 */
export const resetObservationState = () => {
  observationManager.reset();
  observationManager.resetStats();
  console.log(" Observation state reset");
};

/**
 * Stop observation collection
 */
export const stopObservationCollection = () => {
  mlService.stopMonitoring();
  console.log(" Observation collection stopped");
};

/**
 * TEMPORARY TEST MODE ONLY
 * Send a fake observation with hardcoded data for testing
 * Use this to verify backend API, routing, auth, and database saves
 * 
 * DO NOT USE IN PRODUCTION
 * 
 * @param {Object} testData - Optional test data override
 */
export const sendTestObservation = async (testData = {}) => {
  try {
    console.log(" TEST MODE: Sending fake observation");
    console.warn(" This is a TEST observation - not real road data!");

    // Hardcoded test location (Times Square, NYC)
    const payload = {
      latitude: testData.latitude || 40.758896,
      longitude: testData.longitude || -73.985130,
      roadQuality: testData.roadQuality !== undefined ? testData.roadQuality : 2,
      speed: testData.speed || 15.5,
      timestamp: testData.timestamp || new Date().toISOString(),
    };

    console.log(" TEST Payload:", payload);

    await apiRequest("/observations", "POST", payload);

    console.log(" TEST observation sent successfully");
    console.log(" Backend API is working");
    console.log(" Check your database for the new observation");

    return { success: true, payload };
  } catch (error) {
    console.error(" TEST observation failed:", error);
    console.error("Check: 1) BASE_URL 2) Auth token 3) Network connection");
    throw error;
  }
};
