const socketIO = require('socket.io');
const { authenticateSocket } = require('../middleware/socketAuth');
const ActiveSession = require('../models/ActiveSession');
const { getRegionId } = require('../utils/geohash');

/**
 * Helper: update active session safely
 */
const updateSession = (socket, data = {}) => {
    return ActiveSession.findOneAndUpdate(
        { socketId: socket.id },
        {
            ...data,
            lastActivityAt: new Date()
        }
    );
};

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

    io.on('connection', (socket) => {
        console.log(` Socket connected: ${socket.id} (User: ${socket.userId})`);

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

                await updateSession(socket, {
                    currentRegionId: regionId,
                    lastLocation: { latitude, longitude }
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
                        socket.to(oldRegion).emit('user-left-region', {
                            userId: socket.userId,
                            regionId: oldRegion
                        });
                    }

                    socket.join(newRegionId);
                    socket.currentRegion = newRegionId;

                    socket.to(newRegionId).emit('user-joined-region', {
                        userId: socket.userId,
                        regionId: newRegionId
                    });

                    socket.emit('region-changed', {
                        oldRegion,
                        newRegion: newRegionId
                    });
                }

                await updateSession(socket, {
                    currentRegionId: newRegionId,
                    lastLocation: { latitude, longitude }
                });

            } catch (err) {
                console.error('update-location error:', err);
            }
        });

        /**
         * Heartbeat
         */
        socket.on('ping', async () => {
            socket.emit('pong');
            await updateSession(socket);
        });

        /**
         * Disconnect
         */
        socket.on('disconnect', async () => {
            console.log(` Socket disconnected: ${socket.id}`);

            try {
                if (socket.currentRegion) {
                    socket.to(socket.currentRegion).emit('user-left-region', {
                        userId: socket.userId,
                        regionId: socket.currentRegion
                    });
                }

                await ActiveSession.findOneAndUpdate(
                    { socketId: socket.id },
                    { disconnectedAt: new Date() }
                );

            } catch (err) {
                console.error('disconnect cleanup error:', err);
            }
        });
    });

    console.log(' Socket.IO server initialized');
    return io;
}

module.exports = initializeSocketServer;
