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
                        console.error(' Redis: Max reconnection attempts reached');
                        return new Error('Redis reconnection failed');
                    }
                    const delay = Math.min(retries * 100, 3000);
                    console.log(` Redis: Reconnecting in ${delay}ms (attempt ${retries})`);
                    return delay;
                }
            }
        });

        redisClient.on('error', (err) => {
            console.error(' Redis Client Error:', err.message);
            isConnected = false;
        });

        redisClient.on('connect', () => {
            console.log(' Redis: Connecting...');
        });

        redisClient.on('ready', () => {
            console.log(' Redis: Connected and ready');
            isConnected = true;
        });

        redisClient.on('reconnecting', () => {
            console.log(' Redis: Reconnecting...');
            isConnected = false;
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
