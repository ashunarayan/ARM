const geohash = require('ngeohash');

/**
 * Get geohash for a location
 * Precision 6 covers approximately 1.2km × 0.61km
 */
const getGeohash = (latitude, longitude, precision = 6) => {
    return geohash.encode(latitude, longitude, precision);
};

/**
 * Decode geohash to lat/lng
 */
const decodeGeohash = (hash) => {
    return geohash.decode(hash);
};

/**
 * Get bounding box for a geohash
 */
const getGeohashBounds = (hash) => {
    return geohash.decode_bbox(hash);
};

/**
 * Get all neighboring geohashes (8 neighbors + center)
 */
const getNeighbors = (hash) => {
    const neighbors = geohash.neighbors(hash);
    return [hash, ...Object.values(neighbors)];
};

/**
 * Calculate distance between two points (Haversine formula)
 * Returns distance in meters
 */
const calculateDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
        Math.cos(φ1) * Math.cos(φ2) *
        Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // Distance in meters
};

/**
 * Get region ID from coordinates
 */
const getRegionId = (latitude, longitude) => {
    const precision = parseInt(process.env.GEOHASH_PRECISION) || 6;
    return getGeohash(latitude, longitude, precision);
};

module.exports = {
    getGeohash,
    decodeGeohash,
    getGeohashBounds,
    getNeighbors,
    calculateDistance,
    getRegionId
};
