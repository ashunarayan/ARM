/**
 * MapView Component
 * Reusable map component with user location support
 * 
 * ARCHITECTURE:
 * - Presentational component (dumb)
 * - No ML or API logic
 * - Receives markers/segments as props
 * - Emits events via callbacks
 * 
 * USAGE:
 * <MapView
 *   markers={roadMarkers}
 *   onLocationChange={(location) => handleLocationChange(location)}
 * />
 */

import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, View, Text, ActivityIndicator } from 'react-native';
import Mapbox from '@rnmapbox/maps';
import * as Location from 'expo-location';
import type { MapLocation, MapMarker } from '../types';
import { ROAD_QUALITY_COLORS } from '../config/env';
Mapbox.setAccessToken('your-public-pk-token-here');
interface MapViewProps {
    /**
     * Initial center location
     */
    initialLocation?: MapLocation;

    /**
     * Road quality markers to display
     */
    markers?: MapMarker[];

    /**
     * Whether to show user location
     */
    showUserLocation?: boolean;

    /**
     * Whether to follow user location
     */
    followUserLocation?: boolean;

    /**
     * Callback when user location changes
     */
    onLocationChange?: (location: MapLocation) => void;

    /**
     * Callback when map is ready
     */
    onMapReady?: () => void;
}

export const MapView: React.FC<MapViewProps> = ({
    initialLocation,
    markers = [],
    showUserLocation = true,
    followUserLocation = true,
    onLocationChange,
    onMapReady,
}) => {
    const cameraRef = useRef<Mapbox.Camera>(null);
    const [userLocation, setUserLocation] = useState<MapLocation | null>(null);
    const [locationPermission, setLocationPermission] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState(true);

    /**
     * Request location permissions on mount
     */
    useEffect(() => {
        requestLocationPermission();
    }, []);

    const requestLocationPermission = async () => {
        try {
            const { status } = await Location.requestForegroundPermissionsAsync();

            if (status === 'granted') {
                setLocationPermission(true);

                // Get initial location
                const location = await Location.getCurrentPositionAsync({});
                const newLocation: MapLocation = {
                    latitude: location.coords.latitude,
                    longitude: location.coords.longitude,
                    zoom: 15,
                };

                setUserLocation(newLocation);
                onLocationChange?.(newLocation);

                // Watch location updates
                Location.watchPositionAsync(
                    {
                        accuracy: Location.Accuracy.High,
                        distanceInterval: 10, // Update every 10 meters
                    },
                    (location) => {
                        const updatedLocation: MapLocation = {
                            latitude: location.coords.latitude,
                            longitude: location.coords.longitude,
                        };
                        setUserLocation(updatedLocation);
                        onLocationChange?.(updatedLocation);
                    }
                );
            } else {
                console.warn('  Location permission denied');
            }
        } catch (error) {
            console.error('  Failed to get location permission:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleMapReady = () => {
        setIsLoading(false);
        onMapReady?.();
    };

    const centerLocation = userLocation || initialLocation || {
        latitude: 37.7749,
        longitude: -122.4194,
    };

    if (isLoading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#007AFF" />
                <Text style={styles.loadingText}>Loading map...</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Mapbox.MapView
                style={styles.map}
                styleURL={Mapbox.StyleURL.Street}
                onDidFinishLoadingMap={handleMapReady}
            >
                {/* Camera with initial position */}
                <Mapbox.Camera
                    ref={cameraRef}
                    zoomLevel={centerLocation.zoom || 15}
                    centerCoordinate={[centerLocation.longitude, centerLocation.latitude]}
                    followUserLocation={followUserLocation && locationPermission}
                    followZoomLevel={15}
                />

                {/* User Location */}
                {showUserLocation && locationPermission && (
                    <Mapbox.UserLocation
                        visible={true}
                        showsUserHeadingIndicator={true}
                    />
                )}

                {/* Road Quality Markers */}
                {markers.map((marker) => {
                    const MarkerView = () => (
                        <View
                            style={[
                                styles.marker,
                                { backgroundColor: ROAD_QUALITY_COLORS[marker.quality] },
                            ]}
                        />
                    );

                    return (
                        <Mapbox.PointAnnotation
                            key={marker.id}
                            id={marker.id}
                            coordinate={marker.coordinate}
                            children={<MarkerView />}
                        />
                    );
                })}
            </Mapbox.MapView>

            {/* Attribution (required by Mapbox terms) */}
            <View style={styles.attribution}>
                <Text style={styles.attributionText}>© Mapbox © OpenStreetMap</Text>
            </View>
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
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
    },
    loadingText: {
        marginTop: 10,
        fontSize: 16,
        color: '#666',
    },
    marker: {
        width: 12,
        height: 12,
        borderRadius: 6,
        borderWidth: 2,
        borderColor: '#fff',
    },
    attribution: {
        position: 'absolute',
        bottom: 8,
        right: 8,
        backgroundColor: 'rgba(255, 255, 255, 0.8)',
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderRadius: 4,
    },
    attributionText: {
        fontSize: 10,
        color: '#666',
    },
});
