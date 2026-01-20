const Observation = require('../models/Observation');
const RoadSegment = require('../models/RoadSegment');
const User = require('../models/User');
const mapMatchingService = require('../services/mapMatching');
const aggregationService = require('../services/aggregation');
const { getRegionId } = require('../utils/geohash');

/**
 * Submit road quality observation
 */
exports.submitObservation = async (req, res, next) => {
    try {
        const { latitude, longitude, roadQuality, speed, timestamp, deviceMetadata } = req.validatedData;
        const userId = req.userId;

        // Get region ID from coordinates
        const regionId = getRegionId(latitude, longitude);

        // Perform map matching
        const matchResult = await mapMatchingService.matchPoint(latitude, longitude);

        if (!matchResult) {
            return res.status(400).json({
                success: false,
                message: 'Unable to match location to road network'
            });
        }

        // Create observation
        const observation = await Observation.create({
            userId,
            latitude,
            longitude,
            roadQuality,
            speed,
            timestamp: new Date(timestamp),
            regionId,
            roadSegmentId: matchResult.roadSegmentId,
            matchingDistance: matchResult.distance,
            matchingConfidence: matchResult.confidence,
            deviceMetadata
        });

        // Update or create road segment
        let roadSegment = await RoadSegment.findOne({ roadSegmentId: matchResult.roadSegmentId });

        if (!roadSegment) {
            // Create new road segment
            roadSegment = await RoadSegment.create({
                roadSegmentId: matchResult.roadSegmentId,
                geometry: {
                    type: 'LineString',
                    coordinates: [
                        [matchResult.matchedLongitude, matchResult.matchedLatitude],
                        [longitude, latitude]
                    ]
                },
                regionId,
                roadName: matchResult.roadName,
                observationCount: 1,
                lastUpdated: new Date()
            });
        }

        // Trigger aggregation (async, don't wait)
        setImmediate(async () => {
            try {
                const oldScore = roadSegment.aggregatedQualityScore;
                const aggregationResult = await aggregationService.aggregateRoadSegment(matchResult.roadSegmentId);

                if (aggregationResult && aggregationService.shouldBroadcastUpdate(oldScore, aggregationResult.aggregatedQualityScore, aggregationResult.confidenceScore)) {
                    // Broadcast update via Socket.IO (handled in socket server)
                    const io = req.app.get('io');
                    if (io) {
                        io.to(regionId).emit('road-quality-update', {
                            roadSegmentId: matchResult.roadSegmentId,
                            aggregatedQualityScore: aggregationResult.aggregatedQualityScore,
                            confidenceScore: aggregationResult.confidenceScore,
                            regionId,
                            lastUpdated: new Date()
                        });
                    }
                }
            } catch (err) {
                console.error('Aggregation error:', err);
            }
        });

        // Update user statistics
        await User.findByIdAndUpdate(userId, {
            $inc: { totalObservations: 1 },
            lastActive: new Date()
        });

        res.status(201).json({
            success: true,
            message: 'Observation submitted successfully',
            data: {
                observationId: observation._id,
                roadSegmentId: matchResult.roadSegmentId,
                matchingConfidence: matchResult.confidence,
                regionId
            }
        });
    } catch (error) {
        next(error);
    }
};

/**
 * Get user's observation history
 */
exports.getObservationHistory = async (req, res, next) => {
    try {
        const userId = req.userId;
        const { limit = 50, offset = 0 } = req.query;

        const observations = await Observation.find({ userId })
            .sort({ timestamp: -1 })
            .limit(parseInt(limit))
            .skip(parseInt(offset))
            .select('-__v');

        const total = await Observation.countDocuments({ userId });

        res.json({
            success: true,
            data: {
                observations,
                pagination: {
                    total,
                    limit: parseInt(limit),
                    offset: parseInt(offset)
                }
            }
        });
    } catch (error) {
        next(error);
    }
};
