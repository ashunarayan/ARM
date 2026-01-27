const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const { validate } = require('../middleware/validation');
const authenticateFirebase = require('../middleware/firebaseAuth');

/**
 * @route   POST /api/auth/register
 * @desc    Register new user
 * @access  Public
 */
router.post('/register', validate('register'), authController.register);

/**
 * @route   POST /api/auth/login
 * @desc    Login user
 * @access  Public
 */
router.post('/login', validate('login'), authController.login);

/**
 * @route   POST /api/auth/anonymous
 * @desc    Get anonymous device token
 * @access  Public
 */
router.post('/anonymous', validate('anonymous'), authController.anonymous);

/**
 * @route   GET /api/auth/profile
 * @desc    Get current user profile
 * @access  Private
 */
router.get('/profile', authenticateFirebase, authController.getProfile);

module.exports = router;
