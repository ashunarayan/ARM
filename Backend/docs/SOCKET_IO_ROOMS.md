# Socket.IO Room Logic

## Overview

Socket.IO rooms are used to implement **regional broadcasting** - users only receive road quality updates relevant to their current geographic location.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Socket.IO Server                          │
│                                                              │
│  Rooms (Dynamic, Geohash-based):                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Room:      │  │ Room:      │  │ Room:      │            │
│  │ "ttnkbz"   │  │ "ttnkc0"   │  │ "tdr1qw"   │            │
│  │            │  │            │  │            │            │
│  │ Sockets:   │  │ Sockets:   │  │ Sockets:   │            │
│  │ • abc123   │  │ • xyz789   │  │ • def456   │            │
│  │ • ghi234   │  │ • mno890   │  │            │            │
│  │ • jkl345   │  │            │  │            │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│       ↓               ↓               ↓                      │
│  Broadcasts      Broadcasts      Broadcasts                 │
│  only to         only to         only to                    │
│  users in        users in        users in                   │
│  this region     this region     this region                │
└─────────────────────────────────────────────────────────────┘
```

---

## Geohash-Based Regionalization

### Why Geohash?

1. **Hierarchical**: Similar locations have similar prefixes
2. **Fixed Size**: Precision 6 = ~1.2km × 0.61km area
3. **String-based**: Easy to use as room names
4. **Efficient**: O(1) calculation, no database lookup

### Geohash Coverage (Precision 6)

| Precision | Cell Width  | Cell Height | Total Area |
|-----------|-------------|-------------|------------|
| 6         | ±0.61 km    | ±1.22 km    | ~0.74 km²  |

**Example**: New Delhi coordinates (28.6139, 77.2090) → Geohash `ttnkbz`

### Neighboring Regions

```
         North: ttnkc3
            │
West: ttnkc0 ├─── Center: ttnkbz ───┤ East: ttnkc4
            │
         South: ttnkby
```

When querying road data, include neighbors (9 regions total) for seamless map experience.

---

## Room Lifecycle

### 1. Connection & Authentication

```javascript
// Client connects with JWT token
const socket = io('http://localhost:3000', {
  auth: {
    token: 'eyJhbGciOiJIUzI1NiIs...'
  }
});

// Server authenticates
io.use(authenticateSocket);

io.on('connection', (socket) => {
  // Token verified, user attached to socket
  console.log(`User ${socket.userId} connected`);
  
  // Create session record
  ActiveSession.create({
    userId: socket.userId,
    socketId: socket.id,
    connectedAt: new Date()
  });
});
```

---

### 2. Joining a Region

```javascript
// Client sends current location
socket.emit('join-region', {
  latitude: 28.6139,
  longitude: 77.2090
});

// Server calculates geohash and adds to room
socket.on('join-region', async (data) => {
  const { latitude, longitude } = data;
  
  // Calculate region ID (geohash)
  const regionId = getGeohash(latitude, longitude, 6);
  // Result: "ttnkbz"
  
  // Leave previous region if any
  if (socket.currentRegion) {
    socket.leave(socket.currentRegion);
  }
  
  // Join new region room
  socket.join(regionId);
  socket.currentRegion = regionId;
  
  // Update session in database
  await ActiveSession.updateOne(
    { socketId: socket.id },
    { currentRegionId: regionId, lastLocation: { latitude, longitude } }
  );
  
  // Confirm to client
  socket.emit('region-joined', { regionId });
  
  // Notify other users in region
  socket.to(regionId).emit('user-joined-region', {
    userId: socket.userId,
    regionId
  });
});
```

**Room State After:**
```
Room "ttnkbz": [socket1, socket2, socket3, ...]
```

---

### 3. Dynamic Region Switching

User moves to different region while connected:

```javascript
// Client periodically sends location updates
socket.emit('update-location', {
  latitude: 28.6200,  // Moved north
  longitude: 77.2150
});

// Server checks if region changed
socket.on('update-location', async (data) => {
  const { latitude, longitude } = data;
  const newRegionId = getGeohash(latitude, longitude, 6);
  // Result: "ttnkc0" (different from "ttnkbz")
  
  if (socket.currentRegion !== newRegionId) {
    // Leave old room
    socket.leave(socket.currentRegion);
    socket.to(socket.currentRegion).emit('user-left-region', {
      userId: socket.userId,
      regionId: socket.currentRegion
    });
    
    // Join new room
    socket.join(newRegionId);
    socket.to(newRegionId).emit('user-joined-region', {
      userId: socket.userId,
      regionId: newRegionId
    });
    
    // Notify client
    socket.emit('region-changed', {
      oldRegion: socket.currentRegion,
      newRegion: newRegionId
    });
    
    socket.currentRegion = newRegionId;
    
    // Update database
    await ActiveSession.updateOne(
      { socketId: socket.id },
      { currentRegionId: newRegionId, lastLocation: { latitude, longitude } }
    );
  }
});
```

**Room State After:**
```
Room "ttnkbz": [socket1, socket2, ...]      // socket3 left
Room "ttnkc0": [socket4, socket5, socket3]  // socket3 joined
```

---

### 4. Broadcasting Road Quality Updates

When backend processes new observations:

```javascript
// After aggregation service updates road quality
const aggregationResult = await aggregationService.aggregateRoadSegment(roadSegmentId);

// Check if update is significant enough to broadcast
if (shouldBroadcastUpdate(oldScore, newScore, confidence)) {
  const io = req.app.get('io');
  
  // Broadcast ONLY to users in this region
  io.to(regionId).emit('road-quality-update', {
    roadSegmentId: 'seg_286139_772090',
    aggregatedQualityScore: 1.92,
    confidenceScore: 0.82,
    regionId: 'ttnkbz',
    lastUpdated: new Date()
  });
}
```

**Received by:**
- All sockets in room "ttnkbz"
- NOT received by sockets in other rooms

**Client handling:**
```javascript
socket.on('road-quality-update', (data) => {
  console.log('Road updated:', data);
  
  // Update map layer
  updateRoadSegmentOnMap(data.roadSegmentId, {
    quality: data.aggregatedQualityScore,
    confidence: data.confidenceScore
  });
  
  // Show notification if road quality changed significantly
  if (isOnThisRoad(data.roadSegmentId)) {
    showNotification(`Road quality updated: ${getQualityLabel(data.aggregatedQualityScore)}`);
  }
});
```

---

### 5. Disconnect & Cleanup

```javascript
socket.on('disconnect', async () => {
  console.log(`Socket ${socket.id} disconnected`);
  
  // Notify region if user was in one
  if (socket.currentRegion) {
    socket.to(socket.currentRegion).emit('user-left-region', {
      userId: socket.userId,
      regionId: socket.currentRegion
    });
  }
  
  // Remove session from database
  await ActiveSession.deleteOne({ socketId: socket.id });
  
  // Rooms auto-cleanup (Socket.IO handles this)
});
```

---

## Scalability Considerations

### Single Server (Current Implementation)
 Works perfectly for thousands of users
 In-memory rooms (fast)
 No external dependencies

### Multi-Server (Future with Redis Adapter)

When horizontal scaling is needed:

```javascript
const { createAdapter } = require('@socket.io/redis-adapter');
const { createClient } = require('redis');

const pubClient = createClient({ url: 'redis://localhost:6379' });
const subClient = pubClient.duplicate();

io.adapter(createAdapter(pubClient, subClient));
```

**Benefits:**
- Rooms synchronized across servers
- Broadcasts reach all servers
- Load balancing with sticky sessions

**Architecture:**
```
       Load Balancer (Sticky Sessions)
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
Server 1   Server 2   Server 3
    └─────────┼─────────┘
              │
         Redis (Pub/Sub)
```

---

## Room Statistics & Monitoring

### Get active users in a region

```javascript
// Server-side utility
const getUsersInRegion = async (regionId) => {
  const sockets = await io.in(regionId).fetchSockets();
  return {
    regionId,
    userCount: sockets.length,
    socketIds: sockets.map(s => s.id)
  };
};

// Usage
const stats = await getUsersInRegion('ttnkbz');
console.log(stats);
// { regionId: 'ttnkbz', userCount: 15, socketIds: [...] }
```

### Monitor room activity

```javascript
// Periodic stats collection
setInterval(async () => {
  const allRooms = io.sockets.adapter.rooms;
  const roomStats = [];
  
  for (let [roomName, socketSet] of allRooms) {
    // Skip personal rooms (socket.id rooms)
    if (socketSet.size > 1) {
      roomStats.push({
        room: roomName,
        connections: socketSet.size
      });
    }
  }
  
  console.log('Active rooms:', roomStats);
  // [
  //   { room: 'ttnkbz', connections: 12 },
  //   { room: 'ttnkc0', connections: 8 },
  //   ...
  // ]
}, 60000); // Every minute
```

---

## Best Practices

### 1. **Auto-region switching**
Don't require users to manually join regions. Automatically switch based on location updates.

### 2. **Heartbeat/Ping**
Implement periodic ping to keep connection alive and update session activity:
```javascript
setInterval(() => {
  socket.emit('ping');
}, 30000); // Every 30 seconds
```

### 3. **Graceful region transitions**
Ensure smooth transitions when user crosses region boundaries:
- Fetch road data for new region before switching
- Brief overlap to avoid data gaps

### 4. **Limit broadcast frequency**
Don't broadcast every minor update:
```javascript
const shouldBroadcastUpdate = (oldScore, newScore, confidence) => {
  if (confidence < 0.5) return false;  // Low confidence
  if (Math.abs(newScore - oldScore) < 0.3) return false;  // Small change
  return true;
};
```

### 5. **Handle reconnections**
Store last known region in local storage:
```javascript
localStorage.setItem('lastRegion', regionId);

// On reconnect
socket.on('connect', () => {
  const lastRegion = localStorage.getItem('lastRegion');
  if (lastRegion && currentLocation) {
    socket.emit('join-region', currentLocation);
  }
});
```

---

## Testing Room Logic

### Manual test script

```javascript
const io = require('socket.io-client');

// Create multiple test clients
const createClient = (lat, lng, token) => {
  const socket = io('http://localhost:3000', {
    auth: { token }
  });
  
  socket.on('connect', () => {
    console.log('Connected:', socket.id);
    socket.emit('join-region', { latitude: lat, longitude: lng });
  });
  
  socket.on('region-joined', (data) => {
    console.log('Joined region:', data.regionId);
  });
  
  socket.on('road-quality-update', (data) => {
    console.log('Update received:', data);
  });
  
  return socket;
};

// Create 3 clients in same region
const client1 = createClient(28.6139, 77.2090, 'token1');  // ttnkbz
const client2 = createClient(28.6145, 77.2095, 'token2');  // ttnkbz
const client3 = createClient(28.7000, 77.3000, 'token3');  // ttnmxx (different)

// Only client1 and client2 will receive updates for region ttnkbz
```

---

## Summary

| Feature | Implementation |
|---------|----------------|
| **Regionalization** | Geohash (precision 6) ~1.2km coverage |
| **Room Naming** | Direct geohash string (e.g., "ttnkbz") |
| **Dynamic Rooms** | Created on-demand, auto-cleanup |
| **Region Switching** | Automatic based on location updates |
| **Broadcast Scope** | Only users in same region |
| **Scalability** | Redis adapter for multi-server |
| **Session Tracking** | MongoDB TTL collection |

This design ensures efficient, scalable, and user-friendly real-time road quality updates.
