const redis = require('redis');

let redisClient = null;
let isConnected = false;

const initializeRedis = async () => {
    try {
        const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';

        redisClient = redis.createClient({
            url: redisUrl,
            socket: {
                reconnectStrategy: (retries) => {
                    if (retries > 10) {
                        console.error('⚠ Redis: Max reconnection attempts reached');
                        return new Error('Redis reconnection failed');
                    }
                    // Reduce logging spam - only log every 3rd attempt
                    if (retries % 3 === 0) {
                        const delay = Math.min(retries * 100, 3000);
                        console.log(`⚡ Redis: Reconnecting (attempt ${retries})`);
                    }
                    return Math.min(retries * 100, 3000);
                }
            }
        });

        redisClient.on('error', (err) => {
            // Only log unique error messages to avoid spam
            if (!redisClient._lastError || redisClient._lastError !== err.message) {
                console.error(' Redis Client Error:', err.message);
                redisClient._lastError = err.message;
            }
            isConnected = false;
        });

        redisClient.on('ready', () => {
            console.log(' Redis: Connected and ready');
            isConnected = true;
            delete redisClient._lastError;
        });

        redisClient.on('end', () => {
            console.log(' Redis: Connection closed');
            isConnected = false;
        });

        await redisClient.connect();

        // Test connection
        await redisClient.ping();

        return redisClient;
    } catch (error) {
        console.error(' Redis initialization failed:', error.message);
        console.warn(' Server will continue without Redis (graceful degradation)');
        redisClient = null;
        isConnected = false;
        return null;
    }
};

const getRedisClient = () => {
    if (!isConnected || !redisClient) {
        return null;
    }
    return redisClient;
};

const closeRedis = async () => {
    if (redisClient) {
        await redisClient.quit();
        console.log(' Redis connection closed');
    }
};

module.exports = {
    initializeRedis,
    getRedisClient,
    closeRedis
};
