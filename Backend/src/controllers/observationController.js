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

        console.log(" Observation API HIT");
        console.log(" req.body:", req.body);
        console.log(" req.userId:", req.userId);

        const { latitude, longitude, roadQuality, speed, timestamp, deviceMetadata } = req.validatedData;

        console.log(" validatedData:", req.validatedData);

        const userId = req.userId;

        // Get region ID from coordinates
        const regionId = getRegionId(latitude, longitude);

        // Perform map matching
        const matchResult = await mapMatchingService.matchPoint(latitude, longitude);
        console.log(" Map Matching Result:", matchResult);

        if (!matchResult) {
            return res.status(400).json({
                success: false,
                message: 'Unable to match location to road network'
            });
        }

        // Create observation
        const observation = await Observation.create({
            userId,
            location: {
                type: "Point",
                coordinates: [longitude, latitude]
            },
            roadQuality,
            timestamp: new Date(timestamp),
            roadSegmentId: matchResult.roadSegmentId,
            regionId
        });


        // Update or create road segment
        let roadSegment = await RoadSegment.findOneAndUpdate(
            { roadSegmentId: matchResult.roadSegmentId },
            {
                $setOnInsert: {
                    roadSegmentId: matchResult.roadSegmentId,
                    geometry: {
                        type: "LineString",
                        coordinates: [
                            [matchResult.matchedLongitude, matchResult.matchedLatitude],
                            [longitude, latitude]
                        ]
                    },
                    centerPoint: {
                        type: "Point",
                        coordinates: [longitude, latitude]
                    },
                    regionId,
                    roadName: matchResult.roadName
                },
                $inc: { observationCount: 1 },
                $set: { lastUpdated: new Date() }
            },
            { upsert: true, new: true }
        );

        console.log(" RoadSegment saved:", roadSegment.roadSegmentId);
        // Trigger aggregation (async, don't wait)
        setImmediate(async () => {
            try {
                console.log(" Aggregation started for:", matchResult.roadSegmentId);
                const oldScore = roadSegment.aggregatedQualityScore;
                const aggregationResult = await aggregationService.aggregateRoadSegment(matchResult.roadSegmentId);
                console.log(" Aggregation Result:", aggregationResult);

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
