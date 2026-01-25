const { verifyFirebaseToken } = require('../config/firebase');
const User = require('../models/User');

const authenticateFirebase = async (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
                success: false,
                message: 'No token provided'
            });
        }

        const token = authHeader.substring(7);

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

        next();
    } catch (error) {
        return res.status(401).json({
            success: false,
            message: 'Invalid token'
        });
    }
};

module.exports = authenticateFirebase;
