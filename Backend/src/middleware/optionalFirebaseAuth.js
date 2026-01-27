const { verifyFirebaseToken } = require('../config/firebase');
const User = require('../models/User');

/**
 * Optional Firebase authentication - doesn't fail if no token
 * Used for public routes that may optionally use authentication
 */
const optionalAuthenticateFirebase = async (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return next();
        }

        const token = authHeader.substring(7);

        try {
            const decodedToken = await verifyFirebaseToken(token);

            let user = await User.findOne({ firebaseUid: decodedToken.uid });

            if (!user) {
                user = await User.create({
                    firebaseUid: decodedToken.uid,
                    email: decodedToken.email,
                    name: decodedToken.name || decodedToken.email?.split('@')[0],
                    isAnonymous: false,
                });
            }

            user.lastActive = new Date();
            await user.save();

            req.user = user;
            req.userId = user._id;
        } catch (error) {
            // Invalid token, but continue without authentication for optional routes
            console.log('Optional auth failed, continuing without authentication:', error.message);
        }

        next();
    } catch (error) {
        // Continue without authentication
        next();
    }
};

module.exports = optionalAuthenticateFirebase;
