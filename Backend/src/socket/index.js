const socketIO = require('socket.io');
const { authenticateSocket } = require('../middleware/socketAuth');
const { getRegionId } = require('../utils/geohash');
const sessionService = require('../services/sessionService');

function isValidCoordinate(lat, lng) {
    return (
        typeof lat === 'number' &&
        typeof lng === 'number' &&
        lat >= -90 && lat <= 90 &&
        lng >= -180 && lng <= 180
    );
}

function initializeSocketServer(server) {
    const io = socketIO(server, {
        cors: {
            origin: process.env.CORS_ORIGIN || '*',
            methods: ['GET', 'POST'],
            credentials: true
        },
        pingTimeout: Number(process.env.SOCKET_PING_TIMEOUT) || 60000,
        pingInterval: Number(process.env.SOCKET_PING_INTERVAL) || 25000,
        transports: ['websocket', 'polling']
    });

    io.use(authenticateSocket);

    io.on('connection', async (socket) => {
        console.log(` Socket connected: ${socket.id} (User: ${socket.userId})`);

        // Create session in Redis
        await sessionService.createSession(socket.id, socket.userId, {
            userAgent: socket.handshake.headers['user-agent']
        });

        socket.currentRegion = null;

        /**
         * Join region
         */
        socket.on('join-region', async ({ latitude, longitude }) => {
            try {
                if (!isValidCoordinate(latitude, longitude)) {
                    return socket.emit('error', { message: 'Invalid coordinates' });
                }

                const regionId = getRegionId(latitude, longitude);

                if (socket.currentRegion) {
                    socket.leave(socket.currentRegion);
                }

                socket.join(regionId);
                socket.currentRegion = regionId;

                // Update Redis session with region
                await sessionService.joinRegion(socket.id, regionId, {
                    latitude,
                    longitude
                });

                socket.emit('region-joined', { regionId });

                socket.to(regionId).emit('user-joined-region', {
                    userId: socket.userId,
                    regionId
                });

            } catch (err) {
                console.error('join-region error:', err);
                socket.emit('error', { message: 'Join region failed' });
            }
        });

        /**
         * Update location
         */
        socket.on('update-location', async ({ latitude, longitude }) => {
            try {
                if (!isValidCoordinate(latitude, longitude)) return;

                const newRegionId = getRegionId(latitude, longitude);
                const oldRegion = socket.currentRegion;

                if (oldRegion !== newRegionId) {
                    if (oldRegion) {
                        socket.leave(oldRegion);
                        await sessionService.leaveRegion(socket.id, oldRegion);

                        socket.to(oldRegion).emit('user-left-region', {
                            userId: socket.userId,
                            regionId: oldRegion
                        });
                    }

                    socket.join(newRegionId);
                    socket.currentRegion = newRegionId;

                    await sessionService.joinRegion(socket.id, newRegionId, {
                        latitude,
                        longitude
                    });

                    socket.to(newRegionId).emit('user-joined-region', {
                        userId: socket.userId,
                        regionId: newRegionId
                    });

                    socket.emit('region-changed', {
                        oldRegion,
                        newRegion: newRegionId
                    });
                }

                // Update location in session
                await sessionService.updateSession(socket.id, {
                    lastLocation: { latitude, longitude }
                });

            } catch (err) {
                console.error('update-location error:', err);
            }
        });

        /**
         * Road Quality Update
         */
        socket.on('road-quality-update', async (data) => {
            try {
                // data: { quality, location, timestamp }
                const { quality, location } = data;
                
                if (!isValidCoordinate(location.latitude, location.longitude)) return;

                const regionId = getRegionId(location.latitude, location.longitude);

                // Broadcast to everyone in the region (including sender? usually broadcast excludes sender)
                // We perform a broadcast to the region so others see the marker
                socket.to(regionId).emit('road-quality-update', {
                    userId: socket.userId,
                    quality,
                    location,
                    timestamp: Date.now()
                });

                // Optionally save to DB (not implementing fully as per plan focus on realtime map)
                // await roadQualityService.saveReading(socket.userId, data);

            } catch (err) {
                console.error('road-quality-update error:', err);
            }
        });

        /**
         * Heartbeat
         */
        socket.on('ping', async () => {
            socket.emit('pong');
            await sessionService.recordHeartbeat(socket.id);
        });

        /**
         * Disconnect
         */
        socket.on('disconnect', async () => {
            console.log(` Socket disconnected: ${socket.id}`);

            try {
                if (socket.currentRegion) {
                    await sessionService.leaveRegion(socket.id, socket.currentRegion);
                    socket.to(socket.currentRegion).emit('user-left-region', {
                        userId: socket.userId,
                        regionId: socket.currentRegion
                    });
                }

                // Delete session from Redis
                await sessionService.deleteSession(socket.id);

            } catch (err) {
                console.error('disconnect cleanup error:', err);
            }
        });
    });

    console.log(' Socket.IO server initialized');
    return io;
}

module.exports = initializeSocketServer;
