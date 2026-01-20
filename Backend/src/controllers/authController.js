const bcrypt = require('bcryptjs');
const User = require('../models/User');
const { generateToken } = require('../utils/jwt');

/**
 * Register new user
 */
exports.register = async (req, res, next) => {
    try {
        const { email, password, name, deviceId } = req.validatedData;

        // Check if user already exists
        const existingUser = await User.findOne({
            $or: [{ email }, { deviceId }]
        });

        if (existingUser) {
            return res.status(400).json({
                success: false,
                message: 'User with this email or device already exists'
            });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Create user
        const user = await User.create({
            email,
            password: hashedPassword,
            name,
            deviceId,
            isAnonymous: false
        });

        // Generate token
        const token = generateToken({
            userId: user._id,
            deviceId: user.deviceId,
            isAnonymous: false
        });

        res.status(201).json({
            success: true,
            message: 'User registered successfully',
            data: {
                token,
                user: {
                    id: user._id,
                    email: user.email,
                    name: user.name,
                    deviceId: user.deviceId
                }
            }
        });
    } catch (error) {
        next(error);
    }
};

/**
 * Login user
 */
exports.login = async (req, res, next) => {
    try {
        const { email, password, deviceId } = req.validatedData;

        // Find user with password field
        const user = await User.findOne({ email }).select('+password');

        if (!user) {
            return res.status(401).json({
                success: false,
                message: 'Invalid credentials'
            });
        }

        // Check password
        const isValidPassword = await bcrypt.compare(password, user.password);

        if (!isValidPassword) {
            return res.status(401).json({
                success: false,
                message: 'Invalid credentials'
            });
        }

        // Update device ID if changed
        if (user.deviceId !== deviceId) {
            user.deviceId = deviceId;
            await user.save();
        }

        // Generate token
        const token = generateToken({
            userId: user._id,
            deviceId: user.deviceId,
            isAnonymous: false
        });

        res.json({
            success: true,
            message: 'Login successful',
            data: {
                token,
                user: {
                    id: user._id,
                    email: user.email,
                    name: user.name,
                    deviceId: user.deviceId
                }
            }
        });
    } catch (error) {
        next(error);
    }
};

/**
 * Get anonymous device token
 */
exports.anonymous = async (req, res, next) => {
    try {
        const { deviceId } = req.validatedData;

        // Check if anonymous user already exists for this device
        let user = await User.findOne({ deviceId, isAnonymous: true });

        if (!user) {
            // Create anonymous user
            user = await User.create({
                deviceId,
                isAnonymous: true,
                name: `Anonymous_${deviceId.substring(0, 8)}`
            });
        }

        // Generate token
        const token = generateToken({
            userId: user._id,
            deviceId: user.deviceId,
            isAnonymous: true
        });

        res.json({
            success: true,
            message: 'Anonymous token generated',
            data: {
                token,
                user: {
                    id: user._id,
                    deviceId: user.deviceId,
                    isAnonymous: true
                }
            }
        });
    } catch (error) {
        next(error);
    }
};

/**
 * Get current user profile
 */
exports.getProfile = async (req, res, next) => {
    try {
        const user = await User.findById(req.userId);

        res.json({
            success: true,
            data: {
                user: {
                    id: user._id,
                    email: user.email,
                    name: user.name,
                    deviceId: user.deviceId,
                    isAnonymous: user.isAnonymous,
                    totalObservations: user.totalObservations,
                    lastActive: user.lastActive,
                    createdAt: user.createdAt
                }
            }
        });
    } catch (error) {
        next(error);
    }
};
