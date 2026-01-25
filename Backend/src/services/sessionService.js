const { getRedisClient } = require('../config/redis');

/**
 * Redis Session Service
 * Manages ephemeral socket session state with TTL
 * Falls back gracefully if Redis unavailable
 */

const SESSION_TTL = 300; // 5 minutes (for testing)
const HEARTBEAT_TTL = 300; // 5 minutes

/**
 * Store active session in Redis
 */
const createSession = async (socketId, userId, metadata = {}) => {
    const client = getRedisClient();
    if (!client) return false;

    try {
        const sessionKey = `session:${socketId}`;
        const sessionData = {
            socketId,
            userId: userId.toString(),
            connectedAt: new Date().toISOString(),
            ...metadata
        };

        await client.setEx(
            sessionKey,
            SESSION_TTL,
            JSON.stringify(sessionData)
        );

        // Add to user's active sessions set
        const userSessionsKey = `user:${userId}:sessions`;
        await client.sAdd(userSessionsKey, socketId);
        await client.expire(userSessionsKey, SESSION_TTL);

        return true;
    } catch (error) {
        console.error('Redis createSession error:', error.message);
        return false;
    }
};

/**
 * Update session data and refresh TTL
 */
const updateSession = async (socketId, updates = {}) => {
    const client = getRedisClient();
    if (!client) return false;

    try {
        const sessionKey = `session:${socketId}`;
        const existing = await client.get(sessionKey);

        if (!existing) return false;

        const sessionData = {
            ...JSON.parse(existing),
            ...updates,
            lastActivityAt: new Date().toISOString()
        };

        await client.setEx(
            sessionKey,
            SESSION_TTL,
            JSON.stringify(sessionData)
        );

        return true;
    } catch (error) {
        console.error('Redis updateSession error:', error.message);
        return false;
    }
};

/**
 * Get session data
 */
const getSession = async (socketId) => {
    const client = getRedisClient();
    if (!client) return null;

    try {
        const sessionKey = `session:${socketId}`;
        const data = await client.get(sessionKey);
        return data ? JSON.parse(data) : null;
    } catch (error) {
        console.error('Redis getSession error:', error.message);
        return null;
    }
};

/**
 * Delete session
 */
 

const deleteSession = async (socketId) => {
    const client = getRedisClient();
    if (!client) return false;

    try {
        const session = await getSession(socketId);
        if (!session) return false;

        const sessionKey = `session:${socketId}`;
        await client.del(sessionKey);

        // Remove from user's sessions set
        if (session.userId) {
            const userSessionsKey = `user:${session.userId}:sessions`;
            await client.sRem(userSessionsKey, socketId);
        }

        // Leave region
        if (session.currentRegionId) {
            await leaveRegion(socketId, session.currentRegionId);
        }

        return true;
    } catch (error) {
        console.error('Redis deleteSession error:', error.message);
        return false;
    }
};

/**
 * Join region (add socket to region set)
 */
const joinRegion = async (socketId, regionId, location = {}) => {
    const client = getRedisClient();
    if (!client) return false;

    try {
        const regionKey = `region:${regionId}:members`;

        // Add to region members set
        await client.sAdd(regionKey, socketId);
        await client.expire(regionKey, SESSION_TTL);

        // Update session with region info
        await updateSession(socketId, {
            currentRegionId: regionId,
            lastLocation: location
        });

        return true;
    } catch (error) {
        console.error('Redis joinRegion error:', error.message);
        return false;
    }
};

/**
 * Leave region (remove socket from region set)
 */
const leaveRegion = async (socketId, regionId) => {
    const client = getRedisClient();
    if (!client) return false;

    try {
        const regionKey = `region:${regionId}:members`;
        await client.sRem(regionKey, socketId);
        return true;
    } catch (error) {
        console.error('Redis leaveRegion error:', error.message);
        return false;
    }
};

/**
 * Get all members in a region
 */
const getRegionMembers = async (regionId) => {
    const client = getRedisClient();
    if (!client) return [];

    try {
        const regionKey = `region:${regionId}:members`;
        return await client.sMembers(regionKey);
    } catch (error) {
        console.error('Redis getRegionMembers error:', error.message);
        return [];
    }
};

/**
 * Record heartbeat (update last activity)
 */
const recordHeartbeat = async (socketId) => {
    const client = getRedisClient();
    if (!client) return false;

    try {
        const heartbeatKey = `heartbeat:${socketId}`;
        await client.setEx(
            heartbeatKey,
            HEARTBEAT_TTL,
            new Date().toISOString()
        );

        // Also update session activity
        await updateSession(socketId, {});

        return true;
    } catch (error) {
        console.error('Redis recordHeartbeat error:', error.message);
        return false;
    }
};

/**
 * Get all active sessions for a user
 */
const getUserSessions = async (userId) => {
    const client = getRedisClient();
    if (!client) return [];

    try {
        const userSessionsKey = `user:${userId}:sessions`;
        const socketIds = await client.sMembers(userSessionsKey);

        const sessions = [];
        for (const socketId of socketIds) {
            const session = await getSession(socketId);
            if (session) {
                sessions.push(session);
            }
        }

        return sessions;
    } catch (error) {
        console.error('Redis getUserSessions error:', error.message);
        return [];
    }
};

/**
 * Cleanup expired sessions (optional, Redis TTL handles this automatically)
 */
const cleanupExpiredSessions = async () => {
    const client = getRedisClient();
    if (!client) return 0;

    try {
        // This is mostly handled by Redis TTL, but we can scan for orphaned keys
        const pattern = 'session:*';
        let cursor = 0;
        let cleaned = 0;

        do {
            const result = await client.scan(cursor, {
                MATCH: pattern,
                COUNT: 100
            });

            cursor = result.cursor;
            const keys = result.keys;

            for (const key of keys) {
                const ttl = await client.ttl(key);
                if (ttl === -1) {
                    // No TTL set, clean it up
                    await client.del(key);
                    cleaned++;
                }
            }
        } while (cursor !== 0);

        if (cleaned > 0) {
            console.log(`🧹 Cleaned ${cleaned} orphaned sessions`);
        }

        return cleaned;
    } catch (error) {
        console.error('Redis cleanup error:', error.message);
        return 0;
    }
};

module.exports = {
    createSession,
    updateSession,
    getSession,
    deleteSession,
    joinRegion,
    leaveRegion,
    getRegionMembers,
    recordHeartbeat,
    getUserSessions,
    cleanupExpiredSessions
};
