const axios = require('axios');

/**
 * Map matching service using OSRM (OpenStreetMap Routing Machine)
 */
class MapMatchingService {
    constructor() {
        this.baseUrl = process.env.MAP_MATCHING_API_URL || 'http://router.project-osrm.org/match/v1/driving';
    }

    /**
     * Match a single GPS point to nearest road
     * @param {number} latitude 
     * @param {number} longitude 
     * @returns {Object} Matched road segment info
     */
    async matchPoint(latitude, longitude) {
        try {
            // For single point, use nearest service instead of match
            const nearestUrl = this.baseUrl.replace('/match/', '/nearest/');
            const url = `${nearestUrl}/${longitude},${latitude}?number=1`;

            const response = await axios.get(url, { timeout: 5000 });

            if (response.data.code !== 'Ok' || !response.data.waypoints || response.data.waypoints.length === 0) {
                return null;
            }

            const waypoint = response.data.waypoints[0];

            return {
                roadSegmentId: this.generateRoadSegmentId(waypoint),
                matchedLatitude: waypoint.location[1],
                matchedLongitude: waypoint.location[0],
                distance: waypoint.distance || 0, // Distance from original point to matched point
                confidence: this.calculateConfidence(waypoint.distance),
                roadName: waypoint.name || 'Unknown Road'
            };
        } catch (error) {
            console.error('Map matching error:', error.message);
            // Fallback: return original point with low confidence
            return {
                roadSegmentId: this.generateFallbackSegmentId(latitude, longitude),
                matchedLatitude: latitude,
                matchedLongitude: longitude,
                distance: 0,
                confidence: 0.3,
                roadName: 'Unknown Road'
            };
        }
    }

    /**
     * Match multiple GPS points to a route
     * @param {Array} points Array of {latitude, longitude, timestamp}
     * @returns {Object} Matched route info
     */
    async matchRoute(points) {
        try {
            if (!points || points.length < 2) {
                return null;
            }

            // Format coordinates for OSRM (longitude,latitude pairs)
            const coordinates = points.map(p => `${p.longitude},${p.latitude}`).join(';');

            // Add timestamps if available
            const timestamps = points.map(p =>
                p.timestamp ? Math.floor(new Date(p.timestamp).getTime() / 1000) : 0
            ).join(';');

            const url = `${this.baseUrl}/${coordinates}?overview=full&timestamps=${timestamps}&geometries=geojson`;

            const response = await axios.get(url, { timeout: 10000 });

            if (response.data.code !== 'Ok' || !response.data.matchings) {
                return null;
            }

            const matching = response.data.matchings[0];

            return {
                geometry: matching.geometry,
                confidence: matching.confidence || 0.5,
                distance: matching.distance,
                duration: matching.duration
            };
        } catch (error) {
            console.error('Route matching error:', error.message);
            return null;
        }
    }

    /**
     * Generate a unique road segment ID from waypoint
     */
    generateRoadSegmentId(waypoint) {
        // Use location hash as segment ID
        const lat = Math.round(waypoint.location[1] * 10000);
        const lon = Math.round(waypoint.location[0] * 10000);
        return `seg_${lat}_${lon}`;
    }

    /**
     * Generate fallback segment ID when map matching fails
     */
    generateFallbackSegmentId(latitude, longitude) {
        const lat = Math.round(latitude * 10000);
        const lon = Math.round(longitude * 10000);
        return `fallback_${lat}_${lon}`;
    }

    /**
     * Calculate confidence based on matching distance
     * @param {number} distance Distance in meters
     * @returns {number} Confidence score 0-1
     */
    calculateConfidence(distance) {
        if (!distance) return 0.9;
        if (distance < 10) return 0.9;
        if (distance < 30) return 0.7;
        if (distance < 50) return 0.5;
        return 0.3;
    }
}

module.exports = new MapMatchingService();
