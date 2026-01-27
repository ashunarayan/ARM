import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, Platform, PermissionsAndroid } from 'react-native';
import MapboxGL from '@rnmapbox/maps';
import { ENV, ROAD_QUALITY_COLORS, ROAD_QUALITY_LABELS } from '../config/env';
import { mlService } from '../services/mlService';
import { sensorService } from '../services/sensorService';
import { windowManager } from '../services/windowService';
import { socketService } from '../services/socketService';

// Set your public token here or in env.ts
MapboxGL.setAccessToken(ENV.MAPBOX_TOKEN || 'YOUR_MAPBOX_TOKEN'); 

interface MapMarkerState {
    id: string;
    coordinate: [number, number]; // Mapbox uses [lng, lat] array
    quality: number;
    timestamp: number;
}

export const MapScreen = () => {
    const [markers, setMarkers] = useState<MapMarkerState[]>([]);
    const [isMonitoring, setIsMonitoring] = useState(false);
    const [currentQuality, setCurrentQuality] = useState<number | null>(null);
    
    // Services Initialization
    useEffect(() => {
        const initServices = async () => {
             // 1. Initialize Socket
             socketService.connect(ENV.API.BASE_URL);

             // 2. Initialize ML
             await mlService.initialize();

             // 3. Listen for socket updates
             socketService.on('road-quality-update', (data: any) => {
                 // data: { quality, location: { latitude, longitude } }
                 // Mapbox wants [lng, lat]
                 const newMarker: MapMarkerState = {
                     id: `remote-${Date.now()}-${Math.random()}`,
                     coordinate: [data.location.longitude, data.location.latitude],
                     quality: data.quality,
                     timestamp: Date.now()
                 };
                 setMarkers(prev => [...prev.slice(-99), newMarker]);
             });

             // 4. Setup Window Manager Callback (Link Sensor -> ML)
             windowManager.initialize(async (windowData) => {
                 const prediction = await mlService.predict(windowData);
                 if (prediction !== null) {
                     setCurrentQuality(prediction);
                     
                     // Get last location
                     const lastSample = windowData[windowData.length -1];
                     const location = lastSample.location;

                     // Add simple valid check
                     if (location.latitude !== 0 && location.longitude !== 0) {
                         const newMarker: MapMarkerState = {
                             id: `local-${Date.now()}`,
                             coordinate: [location.longitude, location.latitude],
                             quality: prediction,
                             timestamp: Date.now()
                         };
                         setMarkers(prev => [...prev.slice(-99), newMarker]);

                         // Send to Socket (Backend)
                         socketService.sendRoadQualityUpdate(prediction, location);
                     }
                 }
             });
        };

        const requestPerms = async () => {
             if (Platform.OS === 'android') {
                 await PermissionsAndroid.requestMultiple([
                     PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
                     PermissionsAndroid.PERMISSIONS.ACCESS_COARSE_LOCATION
                 ]);
             }
        };

        requestPerms().then(initServices);

        return () => {
            sensorService.stopCollection();
        };
    }, []);

    const toggleMonitoring = async () => {
        if (isMonitoring) {
            sensorService.stopCollection();
            setIsMonitoring(false);
        } else {
            sensorService.startCollection((reading) => {
                windowManager.addReading(reading);
            });
            setIsMonitoring(true);
        }
    };

    return (
        <View style={styles.container}>
            <MapboxGL.MapView
                style={styles.map}
                styleURL="mapbox://styles/mapbox/streets-v12"
                logoEnabled={false}
                attributionEnabled={true}
                onDidFailLoadingMap={() => Alert.alert("Error", "Map failed to load")}
            >
                <MapboxGL.Camera
                    zoomLevel={14}
                    centerCoordinate={[ENV.MAP.DEFAULT_CENTER.longitude, ENV.MAP.DEFAULT_CENTER.latitude]}
                    followUserLocation={true}
                />

                <MapboxGL.UserLocation visible={true} />

                {markers.map(marker => (
                    <MapboxGL.PointAnnotation
                        key={marker.id}
                        id={marker.id}
                        coordinate={marker.coordinate}
                    >
                        <View style={{
                             width: 15, height: 15, borderRadius: 8, 
                             backgroundColor: ROAD_QUALITY_COLORS[marker.quality as 0|1|2|3],
                             borderColor: 'white', borderWidth: 2
                         }} />
                    </MapboxGL.PointAnnotation>
                ))}
            </MapboxGL.MapView>

            <View style={styles.overlay}>
                {currentQuality !== null && (
                     <View style={[styles.badge, { backgroundColor: ROAD_QUALITY_COLORS[currentQuality as 0|1|2|3] }]}>
                         <Text style={styles.badgeText}>
                             Current: {ROAD_QUALITY_LABELS[currentQuality as 0|1|2|3]}
                         </Text>
                     </View>
                )}

                <TouchableOpacity 
                    style={[styles.button, isMonitoring ? styles.buttonStop : styles.buttonStart]} 
                    onPress={toggleMonitoring}
                >
                    <Text style={styles.buttonText}>
                        {isMonitoring ? 'Stop Monitoring' : 'Start Monitoring'}
                    </Text>
                </TouchableOpacity>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: { ...StyleSheet.absoluteFillObject },
    map: { ...StyleSheet.absoluteFillObject },
    overlay: {
        position: 'absolute',
        bottom: 30,
        left: 20,
        right: 20,
        alignItems: 'center'
    },
    badge: {
        padding: 10,
        borderRadius: 20,
        marginBottom: 10,
        elevation: 5
    },
    badgeText: {
        fontWeight: 'bold',
        color: '#fff', 
        textShadowColor: 'rgba(0,0,0,0.5)', 
        textShadowRadius: 2
    },
    button: {
        width: '100%',
        padding: 15,
        borderRadius: 10,
        alignItems: 'center',
        elevation: 5
    },
    buttonStart: { backgroundColor: '#007AFF' },
    buttonStop: { backgroundColor: '#FF3B30' },
    buttonText: { color: 'white', fontWeight: 'bold', fontSize: 16 }
});
