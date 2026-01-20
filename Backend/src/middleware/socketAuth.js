const jwt = require('jsonwebtoken');
const ActiveSession = require('../models/ActiveSession');

/**
 * Middleware to authenticate Socket.IO connections
 */
const authenticateSocket = async (socket, next) => {
    try {
        const token = socket.handshake.auth.token;

        if (!token) {
            return next(new Error('Authentication token required'));
        }

        // Verify JWT token
        const verifyToken = require('../utils/verifyToken');
        const decoded = verifyToken(token);


        // Attach user info to socket
        socket.userId = decoded.userId;
        socket.deviceId = decoded.deviceId;
        socket.isAnonymous = decoded.isAnonymous || false;

        // Create active session
        await ActiveSession.create({
            userId: decoded.userId,
            socketId: socket.id,
            connectedAt: new Date(),
            lastActivityAt: new Date()
        });

        next();
    } catch (error) {
        console.error('Socket authentication error:', error);
        next(new Error('Invalid authentication token'));
    }
};

module.exports = {
    authenticateSocket
};
