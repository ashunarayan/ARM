# MongoDB Schema Design

## Collections Overview

The database consists of 4 main collections:
1. **users** - User accounts and authentication
2. **observations** - Raw road quality observations from mobile devices
3. **roadSegments** - Aggregated road quality data per segment
4. **activeSessions** - Active Socket.IO connections (TTL collection)

---

## 1. users Collection

Stores user authentication and profile information. Supports both registered users and anonymous users.

### Schema
```javascript
{
  _id: ObjectId,
  email: String,              // Optional for anonymous users
  password: String,           // Hashed, select: false
  name: String,
  deviceId: String,           // Unique device identifier (required)
  isAnonymous: Boolean,       // true for anonymous users
  totalObservations: Number,  // Counter for gamification
  lastActive: Date,
  createdAt: Date,
  updatedAt: Date
}
```

### Indexes
```javascript
{ email: 1 }                 // Unique, sparse
{ deviceId: 1 }              // Unique
{ lastActive: -1 }           // For activity queries
```

### Example Document
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "email": "user@example.com",
  "password": "$2a$10$...",
  "name": "John Doe",
  "deviceId": "device-uuid-12345",
  "isAnonymous": false,
  "totalObservations": 150,
  "lastActive": ISODate("2026-01-18T10:30:00Z"),
  "createdAt": ISODate("2026-01-01T00:00:00Z"),
  "updatedAt": ISODate("2026-01-18T10:30:00Z")
}
```

### Notes
- `email` is sparse index to allow null for anonymous users
- `deviceId` is the primary unique identifier
- Anonymous users can later upgrade to full accounts

---

## 2. observations Collection

Stores individual road quality observations submitted by users. This is raw data before aggregation.

### Schema
```javascript
{
  _id: ObjectId,
  userId: ObjectId,              // Reference to users._id
  latitude: Number,              // -90 to 90
  longitude: Number,             // -180 to 180
  location: {                    // GeoJSON Point
    type: "Point",
    coordinates: [Number, Number] // [longitude, latitude]
  },
  roadQuality: Number,           // 0-3 (from ML model)
  speed: Number,                 // m/s
  timestamp: Date,               // From device
  roadSegmentId: String,         // After map matching
  regionId: String,              // Geohash (precision 6)
  processed: Boolean,            // Used in aggregation?
  matchingDistance: Number,      // Meters from GPS to matched road
  matchingConfidence: Number,    // 0-1
  deviceMetadata: {
    platform: String,            // "android", "ios"
    appVersion: String
  },
  createdAt: Date,
  updatedAt: Date
}
```

### Indexes
```javascript
{ location: '2dsphere' }                    // Geospatial queries
{ regionId: 1, timestamp: -1 }              // Region-based queries
{ roadSegmentId: 1, timestamp: -1 }         // Segment aggregation
{ userId: 1, timestamp: -1 }                // User history
{ processed: 1, timestamp: -1 }             // Aggregation queue
```

### Example Document
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439012"),
  "userId": ObjectId("507f1f77bcf86cd799439011"),
  "latitude": 28.6139,
  "longitude": 77.2090,
  "location": {
    "type": "Point",
    "coordinates": [77.2090, 28.6139]
  },
  "roadQuality": 2,
  "speed": 12.5,
  "timestamp": ISODate("2026-01-18T10:30:00Z"),
  "roadSegmentId": "seg_286139_772090",
  "regionId": "ttnkbz",
  "processed": true,
  "matchingDistance": 8.5,
  "matchingConfidence": 0.92,
  "deviceMetadata": {
    "platform": "android",
    "appVersion": "1.0.0"
  },
  "createdAt": ISODate("2026-01-18T10:30:05Z"),
  "updatedAt": ISODate("2026-01-18T10:31:00Z")
}
```

### Notes
- `location` is auto-created from lat/lng in pre-save hook
- `roadSegmentId` is assigned after OSRM map matching
- `processed` flag prevents duplicate aggregations
- Stored permanently for reprocessing/analysis

---

## 3. roadSegments Collection

Stores aggregated road quality data for each road segment. This is the primary data source for map visualization.

### Schema
```javascript
{
  _id: ObjectId,
  roadSegmentId: String,         // Unique segment identifier
  geometry: {                     // GeoJSON LineString
    type: "LineString",
    coordinates: [[Number, Number]] // Array of [lng, lat] pairs
  },
  aggregatedQualityScore: Number, // 0-3 (weighted average)
  confidenceScore: Number,        // 0-1 (data quality measure)
  regionId: String,               // Geohash (precision 6)
  observationCount: Number,       // Total observations
  roadName: String,               // From OSM
  roadType: String,               // highway, residential, etc.
  qualityDistribution: {
    excellent: Number,            // Count of quality 0
    good: Number,                 // Count of quality 1
    bad: Number,                  // Count of quality 2
    worst: Number                 // Count of quality 3
  },
  lastUpdated: Date,
  createdAt: Date,
  updatedAt: Date
}
```

### Indexes
```javascript
{ roadSegmentId: 1 }                        // Unique
{ geometry: '2dsphere' }                    // Geospatial queries
{ regionId: 1, lastUpdated: -1 }            // Region-based queries
{ aggregatedQualityScore: 1 }               // Quality filtering
```

### Example Document
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439013"),
  "roadSegmentId": "seg_286139_772090",
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [77.2090, 28.6139],
      [77.2095, 28.6145],
      [77.2100, 28.6150]
    ]
  },
  "aggregatedQualityScore": 1.85,
  "confidenceScore": 0.78,
  "regionId": "ttnkbz",
  "observationCount": 45,
  "roadName": "Connaught Place Road",
  "roadType": "residential",
  "qualityDistribution": {
    "excellent": 5,
    "good": 15,
    "bad": 20,
    "worst": 5
  },
  "lastUpdated": ISODate("2026-01-18T10:30:00Z"),
  "createdAt": ISODate("2026-01-10T00:00:00Z"),
  "updatedAt": ISODate("2026-01-18T10:30:00Z")
}
```

### Aggregation Logic
```javascript
// Weighted score calculation (from observations)
const now = Date.now();
observations.forEach(obs => {
  const ageHours = (now - obs.timestamp) / (3600 * 1000);
  const timeWeight = Math.exp(-ageHours / 24);     // Time decay
  const speedWeight = obs.speed < 5 ? 1.2 :        // Speed reliability
                      obs.speed > 20 ? 0.7 : 1.0;
  const matchWeight = obs.matchingConfidence;      // Match quality
  
  const weight = timeWeight * speedWeight * matchWeight;
  weightedSum += obs.roadQuality * weight;
  totalWeight += weight;
});

aggregatedQualityScore = weightedSum / totalWeight;
```

### Notes
- Updated asynchronously after new observations
- `confidenceScore` based on sample size, variance, and recency
- Only segments with ≥3 observations get aggregated score
- Geometry updated as more observations received

---

## 4. activeSessions Collection

Tracks active Socket.IO connections for real-time features. Auto-expires after inactivity.

### Schema
```javascript
{
  _id: ObjectId,
  userId: ObjectId,              // Reference to users._id
  socketId: String,              // Socket.IO connection ID
  currentRegionId: String,       // Current geohash region
  lastLocation: {
    latitude: Number,
    longitude: Number
  },
  connectedAt: Date,
  lastActivityAt: Date,          // TTL index on this field
  createdAt: Date,
  updatedAt: Date
}
```

### Indexes
```javascript
{ userId: 1 }                              // User lookup
{ socketId: 1 }                            // Unique
{ currentRegionId: 1 }                     // Region queries
{ lastActivityAt: 1 }, { expireAfterSeconds: 3600 }  // TTL (1 hour)
```

### Example Document
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439014"),
  "userId": ObjectId("507f1f77bcf86cd799439011"),
  "socketId": "abc123xyz",
  "currentRegionId": "ttnkbz",
  "lastLocation": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "connectedAt": ISODate("2026-01-18T10:00:00Z"),
  "lastActivityAt": ISODate("2026-01-18T10:30:00Z"),
  "createdAt": ISODate("2026-01-18T10:00:00Z"),
  "updatedAt": ISODate("2026-01-18T10:30:00Z")
}
```

### Notes
- TTL index auto-deletes documents after 1 hour of inactivity
- Updated on every Socket.IO event (join-region, update-location, ping)
- Used for monitoring active users per region
- Cleaned up automatically on disconnect

---

## Database Sizing Estimates

### For 10,000 active users in India:

**observations** (30 days retention)
- Users: 10,000
- Observations per user per day: 50 (avg 5 hours driving @ 10 Hz, filtered)
- Total per day: 500,000
- 30 days: 15,000,000 documents
- Document size: ~300 bytes
- **Total: ~4.5 GB**

**roadSegments**
- India major roads: ~500,000 road segments
- Document size: ~500 bytes
- **Total: ~250 MB**

**users**
- Active users: 10,000
- Document size: ~200 bytes
- **Total: ~2 MB**

**activeSessions**
- Concurrent users: 1,000 (10% online)
- Document size: ~150 bytes
- **Total: ~150 KB**

**Total Database Size: ~5 GB** (with indexes: ~7-8 GB)

---

## Query Examples

### 1. Get recent observations for a road segment
```javascript
db.observations.find({
  roadSegmentId: "seg_286139_772090",
  timestamp: { $gte: new Date(Date.now() - 24*60*60*1000) }
}).sort({ timestamp: -1 });
```

### 2. Find roads near a location
```javascript
db.roadSegments.find({
  geometry: {
    $near: {
      $geometry: {
        type: "Point",
        coordinates: [77.2090, 28.6139]
      },
      $maxDistance: 5000  // 5km
    }
  }
});
```

### 3. Get all road segments in a region and neighbors
```javascript
const regionIds = ['ttnkbz', 'ttnkc0', 'ttnkc1', ...];  // 9 geohashes
db.roadSegments.find({
  regionId: { $in: regionIds },
  aggregatedQualityScore: { $ne: null }
});
```

### 4. Get user statistics
```javascript
db.users.aggregate([
  {
    $group: {
      _id: null,
      totalUsers: { $sum: 1 },
      anonymousUsers: { $sum: { $cond: ['$isAnonymous', 1, 0] } },
      totalObservations: { $sum: '$totalObservations' }
    }
  }
]);
```

### 5. Region quality statistics
```javascript
db.roadSegments.aggregate([
  {
    $match: { regionId: 'ttnkbz', aggregatedQualityScore: { $ne: null } }
  },
  {
    $group: {
      _id: null,
      avgQuality: { $avg: '$aggregatedQualityScore' },
      totalSegments: { $sum: 1 },
      totalObservations: { $sum: '$observationCount' }
    }
  }
]);
```

---

## Sharding Strategy (Future)

When scaling beyond single server:

### Shard Key: `regionId`
```javascript
sh.shardCollection("roadQuality.observations", { regionId: 1, timestamp: -1 });
sh.shardCollection("roadQuality.roadSegments", { regionId: 1 });
```

### Zone Mapping (India)
```javascript
// North India
sh.addShardTag("shard01", "north");
sh.addTagRange("roadQuality.observations", 
  { regionId: "tt" }, { regionId: "tu" }, "north");

// South India  
sh.addShardTag("shard02", "south");
sh.addTagRange("roadQuality.observations",
  { regionId: "te" }, { regionId: "tf" }, "south");

// East India
sh.addShardTag("shard03", "east");
sh.addTagRange("roadQuality.observations",
  { regionId: "tm" }, { regionId: "tn" }, "east");

// West India
sh.addShardTag("shard04", "west");
sh.addTagRange("roadQuality.observations",
  { regionId: "ts" }, { regionId: "tt" }, "west");
```

This distributes data geographically, optimizing for regional queries.
