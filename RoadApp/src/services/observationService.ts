import { Platform } from 'react-native';
import { apiClient } from './apiClient';
import { Observation, RoadSegment } from '../types';
import { APP_VERSION } from '../config';

export class ObservationService {
    static async submitObservation(
        latitude: number,
        longitude: number,
        roadQuality: 0 | 1 | 2 | 3,
        speed?: number
    ): Promise<void> {
        const observation: Observation = {
            latitude,
            longitude,
            roadQuality,
            timestamp: new Date().toISOString(),
            speed,
            deviceMetadata: {
                model: Platform.select({
                    android: 'Android Device',
                    ios: 'iOS Device',
                    default: 'Unknown',
                }),
                os: `${Platform.OS} ${Platform.Version}`,
                appVersion: APP_VERSION,
            },
        };

        await apiClient.post('/api/observations', observation);
    }

    static async getRoadSegments(
        latitude: number,
        longitude: number,
        radius: number = 5000
    ): Promise<RoadSegment[]> {
        const response = await apiClient.get('/api/roads/segments', {
            params: { latitude, longitude, radius },
        });
        return response.data.segments || [];
    }
}

