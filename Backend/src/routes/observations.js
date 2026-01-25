const express = require('express');
const router = express.Router();
const observationController = require('../controllers/observationController');
const { validate } = require('../middleware/validation');
const authenticateFirebase = require('../middleware/firebaseAuth');

/**
 * @route   POST /api/observations
 * @desc    Submit road quality observation
 * @access  Private
 */
router.post('/', authenticateFirebase, validate('observation'), observationController.submitObservation);

/**
 * @route   GET /api/observations/history
 * @desc    Get user's observation history
 * @access  Private
 */
router.get('/history', authenticateFirebase, observationController.getObservationHistory);

module.exports = router;
