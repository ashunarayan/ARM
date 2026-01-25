/**
 * Road Monitoring Screen
 * Example screen showing Mapbox + ML integration
 * 
 * ARCHITECTURE:
 * - UI layer (presentational)
 * - Uses services for business logic
 * - No direct ML or API calls in UI
 * - Clean separation of concerns
 * 
 * DEMONSTRATES:
 * - Mapbox map with user location
 * - ML road quality monitoring
 * - Automatic observation sending
 * - Road quality markers on map
 */

import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { MapView } from '../../src/components/MapView';
import { mlService } from '../../src/services/ml';
import { observationService } from '../../src/services/observation';
import type { MLInferenceResult, MapMarker } from '../../src/types';
import { ROAD_QUALITY_LABELS } from '../../src/config/env';

export default function RoadMonitoringScreen() {
    const [isMonitoring, setIsMonitoring] = useState(false);
    const [latestResult, setLatestResult] = useState<MLInferenceResult | null>(null);
    const [markers, setMarkers] = useState<MapMarker[]>([]);

    /**
     * Handle ML inference results
     * - Updates UI
     * - Sends to backend
     * - Adds markers to map
     */
    const handleMLResult = async (result: MLInferenceResult) => {
        setLatestResult(result);

        // Add marker to map
        const newMarker: MapMarker = {
            id: `marker-${result.timestamp}`,
            coordinate: [result.location.longitude, result.location.latitude],
            quality: result.roadQuality,
            timestamp: result.timestamp,
        };

        setMarkers((prev) => [...prev.slice(-99), newMarker]); // Keep last 100 markers

        // Send observation to backend
        try {
            await observationService.sendObservation(result);
        } catch (error) {
            console.error('Failed to send observation:', error);
        }
    };

    /**
     * Start monitoring
     */
    const startMonitoring = async () => {
        try {
            if (!mlService.isReady()) {
                Alert.alert('Error', 'ML Service not ready. Please wait and try again.');
                return;
            }

            await mlService.startMonitoring(handleMLResult);
            setIsMonitoring(true);
            Alert.alert('Monitoring Started', 'Road quality monitoring is now active.');
        } catch (error) {
            Alert.alert('Error', 'Failed to start monitoring: ' + (error instanceof Error ? error.message : 'Unknown error'));
        }
    };

    /**
     * Stop monitoring
     */
    const stopMonitoring = () => {
        mlService.stopMonitoring();
        setIsMonitoring(false);
        Alert.alert('Monitoring Stopped', 'Road quality monitoring has been stopped.');
    };

    /**
     * Cleanup on unmount
     */
    useEffect(() => {
        return () => {
            if (isMonitoring) {
                mlService.stopMonitoring();
            }
        };
    }, [isMonitoring]);

    return (
        <View style={styles.container}>
            {/* Map */}
            <MapView
                markers={markers}
                showUserLocation={true}
                followUserLocation={true}
            />

            {/* Control Panel */}
            <View style={styles.controlPanel}>
                {/* Status */}
                <View style={styles.statusContainer}>
                    <Text style={styles.statusLabel}>Status:</Text>
                    <Text style={[styles.statusValue, { color: isMonitoring ? '#34C759' : '#8E8E93' }]}>
                        {isMonitoring ? '● Monitoring' : '○ Stopped'}
                    </Text>
                </View>

                {/* Latest Result */}
                {latestResult && (
                    <View style={styles.resultContainer}>
                        <Text style={styles.resultLabel}>Latest Quality:</Text>
                        <Text style={styles.resultValue}>
                            {ROAD_QUALITY_LABELS[latestResult.roadQuality]}
                        </Text>
                        <Text style={styles.resultMeta}>
                            Speed: {latestResult.speed.toFixed(1)} m/s
                        </Text>
                    </View>
                )}

                {/* Control Button */}
                <TouchableOpacity
                    style={[styles.button, isMonitoring && styles.buttonStop]}
                    onPress={isMonitoring ? stopMonitoring : startMonitoring}
                >
                    <Text style={styles.buttonText}>
                        {isMonitoring ? 'Stop Monitoring' : 'Start Monitoring'}
                    </Text>
                </TouchableOpacity>

                {/* Info */}
                <Text style={styles.infoText}>
                    {markers.length} observations collected
                </Text>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    controlPanel: {
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#fff',
        borderTopLeftRadius: 20,
        borderTopRightRadius: 20,
        padding: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
        elevation: 5,
    },
    statusContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    statusLabel: {
        fontSize: 16,
        fontWeight: '600',
        color: '#000',
        marginRight: 8,
    },
    statusValue: {
        fontSize: 16,
        fontWeight: '700',
    },
    resultContainer: {
        backgroundColor: '#F2F2F7',
        padding: 12,
        borderRadius: 12,
        marginBottom: 16,
    },
    resultLabel: {
        fontSize: 14,
        color: '#8E8E93',
        marginBottom: 4,
    },
    resultValue: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#007AFF',
        marginBottom: 4,
    },
    resultMeta: {
        fontSize: 12,
        color: '#8E8E93',
    },
    button: {
        backgroundColor: '#007AFF',
        paddingVertical: 16,
        borderRadius: 12,
        alignItems: 'center',
        marginBottom: 12,
    },
    buttonStop: {
        backgroundColor: '#FF3B30',
    },
    buttonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
    infoText: {
        textAlign: 'center',
        fontSize: 12,
        color: '#8E8E93',
    },
});
