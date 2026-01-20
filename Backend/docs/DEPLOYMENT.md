# Deployment Guide

## Prerequisites

- **Node.js**: v18+ (LTS recommended)
- **MongoDB**: v6.0+ or MongoDB Atlas
- **npm** or **yarn**
- **Git**

---

## Local Development Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd Road
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Server Configuration
PORT=3000
NODE_ENV=development

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/road_quality_monitoring

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-CHANGE-THIS
JWT_EXPIRY=7d

# Map Matching API (OSRM)
MAP_MATCHING_API_URL=http://router.project-osrm.org/match/v1/driving

# Geohash Configuration
GEOHASH_PRECISION=6

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# Socket.IO Configuration
SOCKET_PING_TIMEOUT=60000
SOCKET_PING_INTERVAL=25000

# Data Aggregation
TIME_DECAY_HOURS=24
MIN_OBSERVATIONS_FOR_AGGREGATION=3
```

### 4. Start MongoDB (Local)

**Option A: Docker**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:6.0
```

**Option B: Local Installation**
```bash
# macOS
brew services start mongodb-community

# Ubuntu
sudo systemctl start mongod

# Windows
net start MongoDB
```

### 5. Run Development Server
```bash
npm run dev
```

Server will start at `http://localhost:3000`

---

## Production Deployment

### Option 1: Traditional VPS (DigitalOcean, AWS EC2, etc.)

#### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Install PM2 (process manager)
sudo npm install -g pm2
```

#### 2. Deploy Application
```bash
# Clone repository
git clone <repository-url>
cd Road

# Install dependencies
npm install --production

# Create .env file
nano .env
# (Add production configuration)

# Start with PM2
pm2 start src/server.js --name road-quality-api

# Save PM2 process list
pm2 save

# Setup PM2 to start on boot
pm2 startup
```

#### 3. Nginx Reverse Proxy

Install Nginx:
```bash
sudo apt install nginx
```

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/road-quality-api
```

Add configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # WebSocket support
    location /socket.io/ {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/road-quality-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 4. SSL Certificate (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

### Option 2: MongoDB Atlas + Cloud Platform

#### 1. Setup MongoDB Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create free cluster
3. Create database user
4. Whitelist IP addresses (0.0.0.0/0 for all IPs)
5. Get connection string

Example connection string:
```
mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/road_quality_monitoring?retryWrites=true&w=majority
```

Update `.env`:
```env
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/road_quality_monitoring?retryWrites=true&w=majority
```

#### 2. Deploy to Heroku

Create `Procfile`:
```
web: node src/server.js
```

Deploy:
```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create road-quality-api

# Set environment variables
heroku config:set NODE_ENV=production
heroku config:set JWT_SECRET=your-super-secret-key
heroku config:set MONGODB_URI=mongodb+srv://...

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

---

### Option 3: Docker Deployment

#### Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 3000

CMD ["node", "src/server.js"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - MONGODB_URI=mongodb://mongo:27017/road_quality_monitoring
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - mongo
    restart: unless-stopped

  mongo:
    image: mongo:6.0
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    restart: unless-stopped

volumes:
  mongo-data:
```

Deploy:
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Environment Variables

### Required
- `MONGODB_URI` - MongoDB connection string
- `JWT_SECRET` - Secret key for JWT tokens (min 32 characters)

### Optional
- `PORT` - Server port (default: 3000)
- `NODE_ENV` - Environment (development/production)
- `CORS_ORIGIN` - Allowed CORS origin (default: *)
- `MAP_MATCHING_API_URL` - OSRM API URL
- `GEOHASH_PRECISION` - Geohash precision (default: 6)
- `RATE_LIMIT_WINDOW_MS` - Rate limit window (default: 900000)
- `RATE_LIMIT_MAX_REQUESTS` - Max requests per window (default: 100)
- `SOCKET_PING_TIMEOUT` - Socket timeout (default: 60000)
- `SOCKET_PING_INTERVAL` - Socket ping interval (default: 25000)
- `TIME_DECAY_HOURS` - Time decay for aggregation (default: 24)
- `MIN_OBSERVATIONS_FOR_AGGREGATION` - Min observations (default: 3)

---

## Database Indexes

Create indexes for optimal performance:

```javascript
// Connect to MongoDB
mongo

// Switch to database
use road_quality_monitoring

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true, sparse: true })
db.users.createIndex({ deviceId: 1 }, { unique: true })
db.users.createIndex({ lastActive: -1 })

db.observations.createIndex({ location: "2dsphere" })
db.observations.createIndex({ regionId: 1, timestamp: -1 })
db.observations.createIndex({ roadSegmentId: 1, timestamp: -1 })
db.observations.createIndex({ userId: 1, timestamp: -1 })
db.observations.createIndex({ processed: 1, timestamp: -1 })

db.roadSegments.createIndex({ roadSegmentId: 1 }, { unique: true })
db.roadSegments.createIndex({ geometry: "2dsphere" })
db.roadSegments.createIndex({ regionId: 1, lastUpdated: -1 })
db.roadSegments.createIndex({ aggregatedQualityScore: 1 })

db.activeSessions.createIndex({ userId: 1 })
db.activeSessions.createIndex({ socketId: 1 }, { unique: true })
db.activeSessions.createIndex({ currentRegionId: 1 })
db.activeSessions.createIndex({ lastActivityAt: 1 }, { expireAfterSeconds: 3600 })
```

---

## Health Monitoring

### PM2 Monitoring
```bash
# View status
pm2 status

# View logs
pm2 logs road-quality-api

# Monitor resources
pm2 monit
```

### Health Check Endpoint
```bash
curl http://localhost:3000/api/health
```

Expected response:
```json
{
  "success": true,
  "message": "API is running",
  "timestamp": "2026-01-18T10:30:00Z"
}
```

---

## Performance Tuning

### MongoDB Connection Pooling
In production, increase pool size:
```javascript
mongoose.connect(uri, {
  maxPoolSize: 50,  // Increase for high traffic
  minPoolSize: 10
});
```

### PM2 Cluster Mode
For multi-core servers:
```bash
pm2 start src/server.js -i max --name road-quality-api
```

### Redis for Socket.IO (Multi-server)
Install Redis adapter:
```bash
npm install @socket.io/redis-adapter redis
```

Update `src/socket/index.js`:
```javascript
const { createAdapter } = require('@socket.io/redis-adapter');
const { createClient } = require('redis');

const pubClient = createClient({ url: process.env.REDIS_URL });
const subClient = pubClient.duplicate();

await pubClient.connect();
await subClient.connect();

io.adapter(createAdapter(pubClient, subClient));
```

---

## Security Checklist

- ✅ Use strong JWT secret (32+ characters)
- ✅ Enable CORS only for trusted origins
- ✅ Use HTTPS in production
- ✅ Keep dependencies updated (`npm audit`)
- ✅ Use environment variables (never commit .env)
- ✅ Enable rate limiting
- ✅ Sanitize user inputs (Joi validation)
- ✅ Use MongoDB authentication
- ✅ Regular backups of database

---

## Backup Strategy

### MongoDB Backup (Automated)
```bash
# Create backup script
nano backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/mongodb"
mkdir -p $BACKUP_DIR

mongodump --uri="mongodb://localhost:27017/road_quality_monitoring" --out="$BACKUP_DIR/backup_$DATE"

# Keep only last 7 days
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} +
```

```bash
chmod +x backup.sh

# Add to cron (daily at 2 AM)
crontab -e
0 2 * * * /path/to/backup.sh
```

---

## Troubleshooting

### Connection Refused
```bash
# Check if server is running
pm2 status

# Check logs
pm2 logs road-quality-api

# Check port
netstat -tlnp | grep 3000
```

### MongoDB Connection Issues
```bash
# Check MongoDB status
sudo systemctl status mongod

# Check connection
mongo --eval "db.adminCommand('ping')"
```

### Socket.IO Not Working
- Ensure WebSocket support in reverse proxy
- Check firewall rules
- Verify CORS configuration

---

## Monitoring & Logging

### Recommended Tools
- **PM2**: Process management
- **MongoDB Atlas**: Managed database + monitoring
- **Datadog/New Relic**: Application performance monitoring
- **Sentry**: Error tracking
- **CloudWatch/Stackdriver**: Cloud platform logs

---

## Scaling Checklist

When you reach thousands of concurrent users:

1. **Enable Redis adapter** for Socket.IO
2. **Setup MongoDB replica set** or use Atlas
3. **Add load balancer** (AWS ALB, Nginx)
4. **Implement caching** (Redis for road segments)
5. **Database sharding** by regionId
6. **CDN** for static assets
7. **Separate microservices** (auth, aggregation, etc.)

---

Your backend is now ready for production! 🚀
