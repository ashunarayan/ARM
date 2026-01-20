const Joi = require('joi');

/**
 * Validation schemas
 */
const schemas = {
    register: Joi.object({
        email: Joi.string().email().required(),
        password: Joi.string().min(6).required(),
        name: Joi.string().min(2).max(50).required(),
        deviceId: Joi.string().required()
    }),

    login: Joi.object({
        email: Joi.string().email().required(),
        password: Joi.string().required(),
        deviceId: Joi.string().required()
    }),

    anonymous: Joi.object({
        deviceId: Joi.string().required()
    }),

    observation: Joi.object({
        latitude: Joi.number().min(-90).max(90).required(),
        longitude: Joi.number().min(-180).max(180).required(),
        roadQuality: Joi.number().integer().min(0).max(3).required(),
        speed: Joi.number().min(0).required(),
        timestamp: Joi.date().iso().required(),
        deviceMetadata: Joi.object({
            platform: Joi.string(),
            appVersion: Joi.string()
        }).optional()
    }),

    nearbyQuery: Joi.object({
        lat: Joi.number().min(-90).max(90).required(),
        lng: Joi.number().min(-180).max(180).required(),
        radius: Joi.number().min(100).max(50000).default(5000) // meters
    })
};

/**
 * Middleware factory for request validation
 */
const validate = (schemaName) => {
    return (req, res, next) => {
        const schema = schemas[schemaName];

        if (!schema) {
            return next(new Error(`Schema '${schemaName}' not found`));
        }

        const { error, value } = schema.validate(req.body, {
            abortEarly: false,
            stripUnknown: true
        });

        if (error) {
            const errors = error.details.map(detail => ({
                field: detail.path.join('.'),
                message: detail.message
            }));

            return res.status(400).json({
                success: false,
                message: 'Validation failed',
                errors
            });
        }

        req.validatedData = value;
        next();
    };
};

/**
 * Query parameter validation
 */
const validateQuery = (schemaName) => {
    return (req, res, next) => {
        const schema = schemas[schemaName];

        if (!schema) {
            return next(new Error(`Schema '${schemaName}' not found`));
        }

        const { error, value } = schema.validate(req.query, {
            abortEarly: false,
            stripUnknown: true
        });

        if (error) {
            const errors = error.details.map(detail => ({
                field: detail.path.join('.'),
                message: detail.message
            }));

            return res.status(400).json({
                success: false,
                message: 'Validation failed',
                errors
            });
        }

        req.validatedQuery = value;
        next();
    };
};

module.exports = {
    validate,
    validateQuery
};
