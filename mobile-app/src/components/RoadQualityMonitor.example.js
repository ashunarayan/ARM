/**
 * Example: Road Quality Monitor Component
 * 
 * This is a reference implementation showing how to integrate
 * the ML pipeline into your React Native screens.
 */

import React, { useEffect, useState } from 'react';
import { View, Text, Button, StyleSheet, ActivityIndicator } from 'react-native';
import { mlService } from '../services/mlService';
import {
    startObservationCollection,
    stopObservationCollection,
    sendObservation
} from '../services/observationService';

export default function RoadQualityMonitor() {
    const [isInitialized, setIsInitialized] = useState(false);
    const [isMonitoring, setIsMonitoring] = useState(false);
    const [latestResult, setLatestResult] = useState(null);
    const [error, setError] = useState(null);

    // Initialize ML service on mount
    useEffect(() => {
        const init = async () => {
            try {
                console.log(' Initializing ML service...');
                await mlService.initialize();
                setIsInitialized(true);
                console.log(' ML service ready');
            } catch (err) {
                console.error(' Initialization failed:', err);
                setError(err.message);
            }
        };

        init();

        return () => {
            // Cleanup on unmount
            if (isMonitoring) {
                mlService.stopMonitoring();
            }
        };
    }, []);

    // Update latest result every second
    useEffect(() => {
        if (!isMonitoring) return;

        const interval = setInterval(() => {
            const result = mlService.getLatestResult();
            if (result) {
                setLatestResult(result);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [isMonitoring]);

    const handleStartMonitoring = async () => {
        try {
            await mlService.startMonitoring();
            setIsMonitoring(true);
            console.log(' Monitoring started');
        } catch (err) {
            console.error(' Failed to start monitoring:', err);
            setError(err.message);
        }
    };

    const handleStopMonitoring = () => {
        mlService.stopMonitoring();
        setIsMonitoring(false);
        console.log(' Monitoring stopped');
    };

    const handleSendObservation = async () => {
        try {
            await sendObservation();
            console.log(' Observation sent');
        } catch (err) {
            console.error(' Failed to send observation:', err);
            setError(err.message);
        }
    };

    const getRoadQualityColor = (quality) => {
        const colors = {
            0: '#DC2626', // very bad - red
            1: '#F59E0B', // bad - orange
            2: '#10B981', // good - green
            3: '#3B82F6', // very good - blue
        };
        return colors[quality] || '#6B7280';
    };

    if (!isInitialized) {
        return (
            <View style={styles.container}>
                <ActivityIndicator size="large" color="#3B82F6" />
                <Text style={styles.loadingText}>Initializing ML service...</Text>
                {error && <Text style={styles.errorText}>{error}</Text>}
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Text style={styles.title}>Road Quality Monitor</Text>

            {/* Status */}
            <View style={styles.statusContainer}>
                <View style={[
                    styles.statusIndicator,
                    { backgroundColor: isMonitoring ? '#10B981' : '#6B7280' }
                ]} />
                <Text style={styles.statusText}>
                    {isMonitoring ? 'Monitoring Active' : 'Monitoring Stopped'}
                </Text>
            </View>

            {/* Latest Result */}
            {latestResult && (
                <View style={styles.resultContainer}>
                    <Text style={styles.resultTitle}>Latest Detection</Text>

                    <View style={[
                        styles.qualityBadge,
                        { backgroundColor: getRoadQualityColor(latestResult.roadQuality) }
                    ]}>
                        <Text style={styles.qualityValue}>{latestResult.roadQuality}</Text>
                        <Text style={styles.qualityLabel}>
                            {mlService.getRoadQualityLabel(latestResult.roadQuality).toUpperCase()}
                        </Text>
                    </View>

                    <View style={styles.metadataContainer}>
                        <Text style={styles.metadataText}>
                             {latestResult.latitude.toFixed(6)}, {latestResult.longitude.toFixed(6)}
                        </Text>
                        <Text style={styles.metadataText}>
                             {latestResult.speed.toFixed(2)} m/s
                        </Text>
                        <Text style={styles.metadataText}>
                             {new Date(latestResult.timestamp).toLocaleTimeString()}
                        </Text>
                    </View>
                </View>
            )}

            {/* Controls */}
            <View style={styles.controlsContainer}>
                {!isMonitoring ? (
                    <Button
                        title="Start Monitoring"
                        onPress={handleStartMonitoring}
                        color="#10B981"
                    />
                ) : (
                    <Button
                        title="Stop Monitoring"
                        onPress={handleStopMonitoring}
                        color="#DC2626"
                    />
                )}

                <View style={styles.spacer} />

                <Button
                    title="Send Observation Now"
                    onPress={handleSendObservation}
                    disabled={!latestResult}
                    color="#3B82F6"
                />
            </View>

            {/* Error Display */}
            {error && (
                <View style={styles.errorContainer}>
                    <Text style={styles.errorText}> {error}</Text>
                </View>
            )}

            {/* Info */}
            <View style={styles.infoContainer}>
                <Text style={styles.infoText}>
                    ℹ Monitoring collects sensor data at 10Hz and runs ML inference every 2 seconds
                </Text>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        padding: 20,
        backgroundColor: '#F9FAFB',
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 20,
        textAlign: 'center',
        color: '#111827',
    },
    statusContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 20,
    },
    statusIndicator: {
        width: 12,
        height: 12,
        borderRadius: 6,
        marginRight: 8,
    },
    statusText: {
        fontSize: 16,
        color: '#374151',
    },
    resultContainer: {
        backgroundColor: '#FFFFFF',
        borderRadius: 12,
        padding: 20,
        marginBottom: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    resultTitle: {
        fontSize: 18,
        fontWeight: '600',
        marginBottom: 15,
        color: '#111827',
    },
    qualityBadge: {
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        borderRadius: 8,
        marginBottom: 15,
    },
    qualityValue: {
        fontSize: 48,
        fontWeight: 'bold',
        color: '#FFFFFF',
    },
    qualityLabel: {
        fontSize: 18,
        fontWeight: '600',
        color: '#FFFFFF',
        marginTop: 5,
    },
    metadataContainer: {
        gap: 8,
    },
    metadataText: {
        fontSize: 14,
        color: '#6B7280',
    },
    controlsContainer: {
        marginBottom: 20,
    },
    spacer: {
        height: 10,
    },
    errorContainer: {
        backgroundColor: '#FEE2E2',
        padding: 15,
        borderRadius: 8,
        marginBottom: 20,
    },
    errorText: {
        color: '#DC2626',
        fontSize: 14,
    },
    infoContainer: {
        backgroundColor: '#DBEAFE',
        padding: 15,
        borderRadius: 8,
    },
    infoText: {
        color: '#1E40AF',
        fontSize: 12,
    },
    loadingText: {
        marginTop: 15,
        fontSize: 16,
        color: '#6B7280',
    },
});
