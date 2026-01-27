import React, { useEffect, useState, useRef } from 'react';
import {
    View,
    StyleSheet,
    Alert,
    TouchableOpacity,
    Text,
    ActivityIndicator,
} from 'react-native';
import Mapbox from '@rnmapbox/maps';
import { MAPBOX_ACCESS_TOKEN } from '../config';
import { ObservationService } from '../services/observationService';
import { MLService } from '../services/mlService';
import { SocketService } from '../services/socketService';
import { RoadSegment, SensorReading } from '../types';
import { AuthService } from '../services/authService';
import auth from '@react-native-firebase/auth';

Mapbox.setAccessToken(MAPBOX_ACCESS_TOKEN);

interface MapScreenProps {
    onSignOut: () => void;
}

export const MapScreen: React.FC<MapScreenProps> = ({ onSignOut }) => {
    const [userLocation] = useState<[number, number]>([-122.4324, 37.78825]);
    const [roadSegments, setRoadSegments] = useState<RoadSegment[]>([]);
    const [loading, setLoading] = useState(false);
    const [collecting, setCollecting] = useState(false);
    const [sensorBuffer, setSensorBuffer] = useState<SensorReading[]>([]);
    const cameraRef = useRef<any>(null);

    const loadRoadSegments = async () => {
        setLoading(true);
        try {
            const segments = await ObservationService.getRoadSegments(
                userLocation[1],
                userLocation[0],
                5000
            );
            setRoadSegments(segments);
        } catch (error) {
            console.error('Failed to load road segments:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadMLModel();
        loadRoadSegments();
        setupSocketConnection();

        return () => {
            SocketService.disconnect();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const setupSocketConnection = async () => {
        try {
            const user = auth().currentUser;
            if (!user) return;

            const token = await user.getIdToken();
            SocketService.connect(token);
            SocketService.joinRegion(userLocation[1], userLocation[0]);

            SocketService.onRoadQualityUpdate((data) => {
                console.log('Road quality update:', data);
                loadRoadSegments();
            });
        } catch (error) {
            console.error('Socket connection failed:', error);
        }
    };

    const loadMLModel = async () => {
        try {
            await MLService.loadModel();
        } catch (error) {
            console.error('Failed to load ML model:', error);
        }
    };

    const handleCollectObservation = async () => {
        setCollecting(true);
        try {
            const mockReadings: SensorReading[] = Array.from({ length: 20 }, (_, i) => ({
                ax: 0.1 + Math.random() * 0.05,
                ay: 0.2 + Math.random() * 0.05,
                az: 9.8 + Math.random() * 0.1,
                wx: Math.random() * 0.02,
                wy: Math.random() * 0.02,
                wz: Math.random() * 0.02,
                speed: 30 + Math.random() * 5,
            }));

            setSensorBuffer(mockReadings);

            const prediction = await MLService.predict({
                readings: mockReadings,
            });

            await ObservationService.submitObservation(
                userLocation[1],
                userLocation[0],
                prediction,
                30
            );

            Alert.alert('Success', `Observation submitted with quality score: ${prediction}`);
            await loadRoadSegments();
        } catch (error: any) {
            Alert.alert('Error', error.message || 'Failed to submit observation');
        } finally {
            setCollecting(false);
        }
    };

    const handleSignOut = async () => {
        try {
            await AuthService.signOut();
            onSignOut();
        } catch {
            Alert.alert('Error', 'Failed to sign out');
        }
    };

    const getColorForScore = (score: number): string => {
        if (score <= 0.5) return '#00FF00';
        if (score <= 1.5) return '#90EE90';
        if (score <= 2.5) return '#FFA500';
        return '#FF0000';
    };

    return (
        <View style={styles.container}>
            <Mapbox.MapView style={styles.map} styleURL={Mapbox.StyleURL.Street}>
                <Mapbox.Camera
                    ref={cameraRef}
                    zoomLevel={14}
                    centerCoordinate={userLocation}
                />
                <Mapbox.UserLocation visible={true} />
                {roadSegments.map((segment) => {
                    const lineStyle = {
                        lineColor: getColorForScore(segment.aggregatedQualityScore),
                        lineWidth: 5,
                    };
                    return (
                        <Mapbox.ShapeSource
                            key={segment.roadSegmentId}
                            id={`segment-${segment.roadSegmentId}`}
                            shape={{
                                type: 'Feature',
                                geometry: segment.geometry,
                                properties: {},
                            }}>
                            <Mapbox.LineLayer
                                id={`line-${segment.roadSegmentId}`}
                                style={lineStyle}
                            />
                        </Mapbox.ShapeSource>
                    );
                })}
            </Mapbox.MapView>
            <View style={styles.controls}>
                <TouchableOpacity
                    style={[styles.button, collecting && styles.buttonDisabled]}
                    onPress={handleCollectObservation}
                    disabled={collecting}>
                    {collecting ? (
                        <ActivityIndicator color="#fff" />
                    ) : (
                        <Text style={styles.buttonText}>Collect Observation</Text>
                    )}
                </TouchableOpacity>
                <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut}>
                    <Text style={styles.signOutText}>Sign Out</Text>
                </TouchableOpacity>
            </View>
            {loading && (
                <View style={styles.loadingOverlay}>
                    <ActivityIndicator size="large" color="#007AFF" />
                </View>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    map: {
        flex: 1,
    },
    controls: {
        position: 'absolute',
        bottom: 40,
        left: 20,
        right: 20,
    },
    button: {
        backgroundColor: '#007AFF',
        height: 50,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 10,
    },
    buttonDisabled: {
        opacity: 0.6,
    },
    buttonText: {
        color: '#fff',
        fontSize: 18,
        fontWeight: '600',
    },
    signOutButton: {
        backgroundColor: '#FF3B30',
        height: 40,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
    },
    signOutText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
    loadingOverlay: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: 'rgba(0,0,0,0.3)',
        justifyContent: 'center',
        alignItems: 'center',
    },
});
