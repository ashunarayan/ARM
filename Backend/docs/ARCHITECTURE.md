# Backend Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Mobile Application                          │
│  ┌────────────┐    ┌──────────────┐    ┌───────────────────────┐   │
│  │  TinyML    │───▶│ Calibration  │───▶│ Road Quality (0-3)    │   │
│  │  (On-device)│    │   (Gravity)  │    │ + GPS + Speed         │   │
│  └────────────┘    └──────────────┘    └───────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ HTTP POST (Observations)
                               │ WebSocket (Real-time updates)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Backend Server (Node.js)                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      Express REST API                          │ │
│  │  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐  │ │
│  │  │   Auth   │  │ Observations │  │    Roads/Regions       │  │ │
│  │  │  (JWT)   │  │  Controller  │  │     Controller         │  │ │
│  │  └──────────┘  └──────────────┘  └────────────────────────┘  │ │
│  └──────────────────────┬─────────────────────────────────────────┘ │
│                         │                                            │
│  ┌─────────────────────┴────────────────────────────────────────┐  │
│  │              Core Processing Layer                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │ Map Matching │  │   Geohash    │  │   Aggregation    │  │  │
│  │  │   Service    │  │   Service    │  │    Service       │  │  │
│  │  │   (OSRM)     │  │ (ngeohash)   │  │ (Time Decay +    │  │  │
│  │  │              │  │              │  │  Weighted Avg)   │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │  │
│  └──────────────────────┬───────────────────────────────────────┘  │
│                         │                                            │
│  ┌─────────────────────┴────────────────────────────────────────┐  │
│  │              Socket.IO Real-time Server                      │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  Regional Rooms (Geohash-based)                        │ │  │
│  │  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐       │ │  │
│  │  │  │ Room:  │  │ Room:  │  │ Room:  │  │ Room:  │       │ │  │
│  │  │  │ tdr1qw │  │ tdr1qx │  │ tdr1qy │  │  ...   │       │ │  │
│  │  │  └────────┘  └────────┘  └────────┘  └────────┘       │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Storage Layer                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  MongoDB (Persistent Domain Data)                            │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│  │  │  users   │  │ observations │  │   roadSegments       │  │  │
│  │  │          │  │              │  │                      │  │  │
│  │  │ deviceId │  │ location     │  │ roadSegmentId        │  │  │
│  │  │ email    │  │ roadQuality  │  │ geometry (GeoJSON)   │  │  │
│  │  │ isAnon   │  │ timestamp    │  │ qualityScore         │  │  │
│  │  │          │  │ regionId     │  │ observationCount     │  │  │
│  │  └──────────┘  └──────────────┘  └──────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Redis (Ephemeral Session State - TTL Auto-Expire)          │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │  │
│  │  │ Active Sessions│  │ Region Members │  │  Heartbeats  │  │  │
│  │  │ session:{id}   │  │ region:{id}    │  │ heartbeat:*  │  │  │
│  │  │ (1h TTL)       │  │ (1h TTL)       │  │ (5min TTL)   │  │  │
│  │  └────────────────┘  └────────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 External Services                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  OpenStreetMap Routing Machine (OSRM)                        │  │
│  │  - Map matching API                                           │  │
│  │  - GPS point → Road segment                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

### 1. User Registration/Authentication
```
Mobile App → POST /api/auth/register → JWT Token
Mobile App → POST /api/auth/login → JWT Token
Mobile App → POST /api/auth/anonymous → JWT Token (deviceId)
```

### 2. Socket.IO Connection & Regional Room
```
Mobile App → WebSocket Connect (with JWT) → Server authenticates
Mobile App → emit('join-region', {lat, lng}) → Server calculates geohash
Server → socket.join(regionId) → User added to regional room
Server → emit('region-joined') → Confirmation to user
```

### 3. Road Quality Observation Submission
```
Mobile App → POST /api/observations
             {latitude, longitude, roadQuality, speed, timestamp}
                     │
                     ▼
             ┌─────────────────┐
             │  Map Matching   │
             │  Service (OSRM) │
             └────────┬────────┘
                      │
                      ▼ {roadSegmentId, matchedLat, matchedLng, confidence}
             ┌────────────────────┐
             │ Save Observation   │
             │ to MongoDB         │
             └────────┬───────────┘
                      │
                      ▼
             ┌────────────────────┐
             │ Update/Create      │
             │ RoadSegment        │
             └────────┬───────────┘
                      │
                      ▼
             ┌────────────────────┐
             │ Trigger Aggregation│
             │ (Async)            │
             └────────┬───────────┘
                      │
                      ▼
             Get recent observations → Calculate weighted score
             Time decay + speed weight → Update aggregatedQualityScore
                      │
                      ▼
             Check if update is significant
                      │
                      ▼
             io.to(regionId).emit('road-quality-update', data)
                      │
                      ▼
Mobile Apps in same region receive update in real-time
```

### 4. Real-time Regional Updates
```
User drives → Location changes → emit('update-location', {lat, lng})
                     │
                     ▼
             Calculate new geohash
                     │
                     ▼
             Region changed?
                     │
                 ┌───┴───┐
                Yes      No
                 │        │
                 ▼        ▼
          Leave old room  Update session
          Join new room       │
          Notify users        │
                 │            │
                 └────┬───────┘
                      ▼
             User now in correct regional room
```

## Regional Segmentation (Geohash)

### Geohash Precision 6 Coverage
- **Area**: ~1.2 km × 0.61 km (~0.73 km²)
- **Perfect for**: City-level road monitoring
- **Example**: Coordinates (28.6139, 77.2090) → Geohash "ttnkbz"

### Regional Room Strategy
```
User Location (28.6139, 77.2090)
         ↓
Calculate Geohash (precision 6) = "ttnkbz"
         ↓
Socket.IO Room = "ttnkbz"
         ↓
All users in this ~1.2km radius join same room
         ↓
Road updates broadcast ONLY to this room
```

### Neighboring Regions
```
When fetching road data, include neighbors:
  
  ┌────────┬────────┬────────┐
  │ ttnkc2 │ ttnkc3 │ ttnkc6 │
  ├────────┼────────┼────────┤
  │ ttnkc0 │ ttnkbz │ ttnkc4 │  ← User here
  ├────────┼────────┼────────┤
  │ ttnkbx │ ttnkby │ ttnkc1 │
  └────────┴────────┴────────┘
  
  Total 9 regions fetched for smooth map experience
```

## Scalability Architecture

### Horizontal Scaling (Future)
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Server 1     │     │ Server 2     │     │ Server 3     │
│ (Port 3000)  │     │ (Port 3001)  │     │ (Port 3002)  │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                ┌───────────▼──────────┐
                │  Redis Adapter       │
                │  (Socket.IO sync)    │
                └───────────┬──────────┘
                            │
                ┌───────────▼──────────┐
                │  Load Balancer       │
                │  (Sticky Sessions)   │
                └──────────────────────┘
```

### Database Sharding Strategy
```
Shard Key: regionId (geohash)
  
  Shard 1: Regions starting with "tt" (North India)
  Shard 2: Regions starting with "te" (South India)
  Shard 3: Regions starting with "tm" (East India)
  Shard 4: Regions starting with "ts" (West India)
```

## Security

### Authentication Flow
```
1. Register/Login → JWT Token generated
2. Token contains: {userId, deviceId, isAnonymous}
3. REST API requests: Authorization: Bearer <token>
4. Socket.IO: socket.handshake.auth.token = <token>
5. Token verification on every request/connection
```

### Anonymous Users
```
POST /api/auth/anonymous {deviceId}
  ↓
Create user with isAnonymous: true
  ↓
Generate JWT (same structure)
  ↓
Full access to submit observations
  ↓
Can upgrade to full account later
```

## Performance Optimizations

### 1. Database Indexes
- `observations`: `{location: '2dsphere'}`, `{regionId: 1, timestamp: -1}`
- `roadSegments`: `{geometry: '2dsphere'}`, `{regionId: 1}`
- `users`: `{deviceId: 1}`, `{email: 1}`
- `activeSessions`: `{socketId: 1}`, TTL index on `lastActivityAt`

### 2. Aggregation Caching
- Don't aggregate on every observation
- Minimum 3 observations required
- Only broadcast significant changes (>0.3 score difference)

### 3. Map Matching
- Timeout: 5 seconds
- Fallback to original coordinates if OSRM fails
- Batch matching for route history (future feature)

### 4. Socket.IO Rooms
- Dynamic room creation (no pre-loading)
- Auto-cleanup on disconnect
- Region-based isolation (no global broadcasts)

## Monitoring & Observability

### Key Metrics
- Active Socket.IO connections per region
- Observation submission rate
- Map matching success rate
- Aggregation processing time
- Database query performance

### Health Check
```
GET /api/health
{
  "success": true,
  "message": "API is running",
  "timestamp": "2026-01-18T..."
}
```
