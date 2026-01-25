# Redis Integration Guide

## Overview

The backend now uses **Redis** for all ephemeral, fast-changing session/socket state, while **MongoDB** remains the source of truth for persistent domain data.

## Architecture

### Data Separation

**Redis (Ephemeral State - TTL-based):**
- Active socket sessions
- User presence/online status
- Region membership (which users are in which geohash regions)
- Heartbeat tracking
- All data expires automatically (1 hour TTL by default)

**MongoDB (Persistent Domain Data):**
- Users
- Observations (road quality data)
- RoadSegments (aggregated quality per segment)
- Historical analytics data

## Configuration

### Environment Variables

```bash
# Redis Connection URL
REDIS_URL=redis://localhost:6379           # Local development
REDIS_URL=redis://redis:6379               # Docker Compose
REDIS_URL=rediss://your-cache.redis.cache.windows.net:6380  # Azure
REDIS_URL=redis://your-cluster.cache.amazonaws.com:6379     # AWS
```

### Local Development

**Option 1: Docker Compose (Recommended)**
```bash
cd Backend
docker-compose up -d redis
npm run dev
```

**Option 2: Local Redis**
```bash
# Install Redis
# Windows: https://github.com/microsoftarchive/redis/releases
# Mac: brew install redis
# Linux: sudo apt install redis

# Start Redis
redis-server

# Start backend
npm run dev
```

### Production Deployment

**Docker Compose:**
```bash
docker-compose up -d
```

**Cloud Managed Redis:**
- **Azure Cache for Redis**: Use connection string with SSL (rediss://)
- **AWS ElastiCache**: Use cluster endpoint
- **Google Cloud Memorystore**: Use internal IP

## Redis Data Structure

### Session Keys
```
session:{socketId}          → JSON session data (1h TTL)
user:{userId}:sessions      → Set of socket IDs (1h TTL)
heartbeat:{socketId}        → Last heartbeat timestamp (5min TTL)
```

### Region Keys
```
region:{regionId}:members   → Set of socket IDs in region (1h TTL)
```

### Example Session Data
```json
{
  "socketId": "abc123",
  "userId": "507f1f77bcf86cd799439011",
  "currentRegionId": "ttngkc",
  "lastLocation": {
    "latitude": 28.7037,
    "longitude": 77.2079
  },
  "connectedAt": "2026-01-24T10:30:00Z",
  "lastActivityAt": "2026-01-24T10:45:23Z",
  "userAgent": "mobile-app/1.0"
}
```

## API Changes

### Health Check Endpoint

**GET /health**
```json
{
  "status": "ok",
  "timestamp": "2026-01-24T10:30:00Z",
  "services": {
    "mongodb": "connected",
    "redis": "connected",
    "socketio": "active"
  }
}
```

## Graceful Degradation

If Redis is unavailable:
- Server continues to run (no crash)
- Socket.IO still functions
- Session state is not persisted
- Logs warning: `⚠️ Server will continue without Redis`

## Horizontal Scaling

### Socket.IO with Redis Adapter (Future Enhancement)

For multi-server deployments, add the Redis adapter:

```bash
npm install @socket.io/redis-adapter
```

```javascript
const { createAdapter } = require("@socket.io/redis-adapter");
const { createClient } = require("redis");

const pubClient = createClient({ url: process.env.REDIS_URL });
const subClient = pubClient.duplicate();

await Promise.all([pubClient.connect(), subClient.connect()]);

io.adapter(createAdapter(pubClient, subClient));
```

This enables:
- Multiple backend servers
- Load balancer distribution
- Cross-server socket events
- Shared session state

## Monitoring

### Redis CLI Commands

```bash
# Connect to Redis
redis-cli

# View all session keys
KEYS session:*

# Get session data
GET session:{socketId}

# View region members
SMEMBERS region:ttngkc:members

# Check TTL
TTL session:{socketId}

# Monitor live commands
MONITOR

# Check memory usage
INFO memory

# View connected clients
CLIENT LIST
```

### Health Monitoring

```bash
# Check Redis connection
curl http://localhost:5000/health

# Redis ping
redis-cli ping
```

## Migration Notes

### Breaking Changes
**NONE** - Mobile app and ML pipeline remain unchanged.

### Data Migration
No migration needed. ActiveSession MongoDB collection is no longer used but can remain for historical reference.

### Rollback Plan
1. Comment out Redis initialization in `server.js`
2. Restore old `socket/index.js` (uses ActiveSession model)
3. Restart server

## Performance Benefits

| Metric | MongoDB (Before) | Redis (After) |
|--------|------------------|---------------|
| Session Write | ~10-50ms | <1ms |
| Session Read | ~5-20ms | <1ms |
| Region Query | ~20-100ms | <1ms |
| TTL Cleanup | Manual/Cron | Automatic |
| Memory Usage | Persistent | Optimized (LRU) |

## Security

### Redis Authentication (Production)

```bash
# .env
REDIS_URL=redis://:your-password@host:6379
```

### Network Security
- Use private network for Redis (no public exposure)
- Enable SSL/TLS for cloud deployments (rediss://)
- Firewall rules: Only backend servers can access Redis

## Troubleshooting

### Redis Connection Failed
```
❌ Redis Client Error: connect ECONNREFUSED 127.0.0.1:6379
⚠️ Server will continue without Redis
```
**Solution**: Start Redis server or update REDIS_URL

### Session Not Found
**Cause**: Session expired (1h TTL) or Redis unavailable  
**Solution**: Client reconnects and creates new session

### Memory Issues
```bash
# Set max memory in docker-compose.yml
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## Testing

```bash
# Start services
docker-compose up -d

# Check health
curl http://localhost:5000/health

# Connect mobile app
# Sessions automatically created in Redis

# Monitor Redis
redis-cli MONITOR
```

## Further Reading

- [Redis Documentation](https://redis.io/docs/)
- [Socket.IO Redis Adapter](https://socket.io/docs/v4/redis-adapter/)
- [Azure Cache for Redis](https://azure.microsoft.com/en-us/services/cache/)
- [AWS ElastiCache](https://aws.amazon.com/elasticache/)
