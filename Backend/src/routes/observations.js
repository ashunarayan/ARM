const express = require('express');
const router = express.Router();
const observationController = require('../controllers/observationController');
const { validate } = require('../middleware/validation');
const { authenticate } = require('../middleware/auth');

/**
 * @route   POST /api/observations
 * @desc    Submit road quality observation
 * @access  Private
 */
router.post('/', authenticate, validate('observation'), observationController.submitObservation);

/**
 * @route   GET /api/observations/history
 * @desc    Get user's observation history
 * @access  Private
 */
router.get('/history', authenticate, observationController.getObservationHistory);

module.exports = router;
