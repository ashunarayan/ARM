const { verifyFirebaseToken } = require('../config/firebase');
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

        // Verify Firebase token
        const decodedToken = await verifyFirebaseToken(token);

        // Attach user info to socket
        socket.userId = decodedToken.uid;
        socket.email = decodedToken.email;
        socket.isAnonymous = false;

        // Create active session
        await ActiveSession.findOneAndUpdate(
            { socketId: socket.id },
            {
                userId: decodedToken.uid,
                socketId: socket.id,
                connectedAt: new Date(),
                lastActivityAt: new Date()
            },
            { upsert: true, new: true }
        );

        next();
    } catch (error) {
        console.error('Socket authentication error:', error);
        next(new Error('Invalid authentication token'));
    }
};

module.exports = {
    authenticateSocket
};
