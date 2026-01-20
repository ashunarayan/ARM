# API Documentation

## Base URL
```
http://localhost:3000/api
```

## Authentication

All authenticated endpoints require JWT token in header:
```
Authorization: Bearer <token>
```

---

## Auth Endpoints

### 1. Register User
**POST** `/api/auth/register`

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe",
  "deviceId": "device-uuid-12345"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "name": "John Doe",
      "deviceId": "device-uuid-12345"
    }
  }
}
```

---

### 2. Login User
**POST** `/api/auth/login`

Login with existing account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "deviceId": "device-uuid-12345"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "name": "John Doe",
      "deviceId": "device-uuid-12345"
    }
  }
}
```

---

### 3. Anonymous Authentication
**POST** `/api/auth/anonymous`

Get token for anonymous usage (no email/password required).

**Request Body:**
```json
{
  "deviceId": "device-uuid-12345"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Anonymous token generated",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "deviceId": "device-uuid-12345",
      "isAnonymous": true
    }
  }
}
```

---

### 4. Get Profile
**GET** `/api/auth/profile`

Get current user profile (requires authentication).

**Response (200):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "name": "John Doe",
      "deviceId": "device-uuid-12345",
      "isAnonymous": false,
      "totalObservations": 150,
      "lastActive": "2026-01-18T10:30:00Z",
      "createdAt": "2026-01-01T00:00:00Z"
    }
  }
}
```

---

## Observation Endpoints

### 5. Submit Observation
**POST** `/api/observations` (Authenticated)

Submit a road quality observation from mobile device.

**Request Body:**
```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "roadQuality": 2,
  "speed": 12.5,
  "timestamp": "2026-01-18T10:30:00Z",
  "deviceMetadata": {
    "platform": "android",
    "appVersion": "1.0.0"
  }
}
```

**Field Details:**
- `roadQuality`: Integer 0-3 (0=best, 1=good, 2=bad, 3=worst)
- `speed`: Float in m/s
- `timestamp`: ISO 8601 format

**Response (201):**
```json
{
  "success": true,
  "message": "Observation submitted successfully",
  "data": {
    "observationId": "507f1f77bcf86cd799439011",
    "roadSegmentId": "seg_286139_772090",
    "matchingConfidence": 0.9,
    "regionId": "ttnkbz"
  }
}
```

---

### 6. Get Observation History
**GET** `/api/observations/history` (Authenticated)

Get user's observation history.

**Query Parameters:**
- `limit` (optional): Number of records (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Example:**
```
GET /api/observations/history?limit=20&offset=0
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "observations": [
      {
        "_id": "507f1f77bcf86cd799439011",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "roadQuality": 2,
        "speed": 12.5,
        "timestamp": "2026-01-18T10:30:00Z",
        "regionId": "ttnkbz",
        "roadSegmentId": "seg_286139_772090",
        "matchingConfidence": 0.9
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 20,
      "offset": 0
    }
  }
}
```

---

## Road Endpoints

### 7. Get Road Segments by Region
**GET** `/api/roads/region/:regionId`

Get all road segments in a specific region (geohash).

**Query Parameters:**
- `includeNeighbors` (optional): Include neighboring regions (default: true)

**Example:**
```
GET /api/roads/region/ttnkbz?includeNeighbors=true
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "regionId": "ttnkbz",
    "roadSegments": [
      {
        "roadSegmentId": "seg_286139_772090",
        "geometry": {
          "type": "LineString",
          "coordinates": [[77.2090, 28.6139], [77.2095, 28.6145]]
        },
        "aggregatedQualityScore": 1.85,
        "confidenceScore": 0.78,
        "regionId": "ttnkbz",
        "observationCount": 45,
        "roadName": "Connaught Place Road",
        "lastUpdated": "2026-01-18T10:30:00Z",
        "qualityDistribution": {
          "excellent": 5,
          "good": 15,
          "bad": 20,
          "worst": 5
        }
      }
    ],
    "count": 12
  }
}
```

---

### 8. Get Nearby Road Segments
**GET** `/api/roads/nearby`

Get road segments near a specific location.

**Query Parameters:**
- `lat`: Latitude (required)
- `lng`: Longitude (required)
- `radius`: Radius in meters (optional, default: 5000, max: 50000)

**Example:**
```
GET /api/roads/nearby?lat=28.6139&lng=77.2090&radius=2000
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "location": {
      "latitude": 28.6139,
      "longitude": 77.2090
    },
    "radius": 2000,
    "roadSegments": [
      {
        "roadSegmentId": "seg_286139_772090",
        "geometry": {...},
        "aggregatedQualityScore": 1.85,
        "confidenceScore": 0.78,
        "distance": 150.5,
        "roadName": "Connaught Place Road"
      }
    ],
    "count": 8
  }
}
```

---

### 9. Get Road Segment Details
**GET** `/api/roads/segment/:segmentId`

Get detailed information about a specific road segment.

**Example:**
```
GET /api/roads/segment/seg_286139_772090
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "roadSegment": {
      "roadSegmentId": "seg_286139_772090",
      "geometry": {
        "type": "LineString",
        "coordinates": [[77.2090, 28.6139], [77.2095, 28.6145]]
      },
      "aggregatedQualityScore": 1.85,
      "confidenceScore": 0.78,
      "regionId": "ttnkbz",
      "observationCount": 45,
      "roadName": "Connaught Place Road",
      "roadType": "residential",
      "lastUpdated": "2026-01-18T10:30:00Z",
      "qualityDistribution": {
        "excellent": 5,
        "good": 15,
        "bad": 20,
        "worst": 5
      }
    }
  }
}
```

---

### 10. Get Region Statistics
**GET** `/api/roads/region/:regionId/stats`

Get aggregated statistics for all roads in a region.

**Example:**
```
GET /api/roads/region/ttnkbz/stats
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "regionId": "ttnkbz",
    "statistics": {
      "totalSegments": 25,
      "averageQuality": 1.65,
      "totalObservations": 1250,
      "excellentRoads": 8,
      "goodRoads": 10,
      "badRoads": 5,
      "worstRoads": 2
    }
  }
}
```

---

## WebSocket Events (Socket.IO)

### Connection
```javascript
const socket = io('http://localhost:3000', {
  auth: {
    token: 'your-jwt-token-here'
  }
});
```

---

### Client → Server Events

#### 1. join-region
Join a regional room based on current location.

**Emit:**
```javascript
socket.emit('join-region', {
  latitude: 28.6139,
  longitude: 77.2090
});
```

**Receive:**
```javascript
socket.on('region-joined', (data) => {
  console.log(data);
  // {
  //   regionId: 'ttnkbz',
  //   latitude: 28.6139,
  //   longitude: 77.2090,
  //   timestamp: '2026-01-18T10:30:00Z'
  // }
});
```

---

#### 2. leave-region
Leave current regional room.

**Emit:**
```javascript
socket.emit('leave-region');
```

**Receive:**
```javascript
socket.on('region-left', (data) => {
  console.log(data);
  // { regionId: 'ttnkbz' }
});
```

---

#### 3. update-location
Update current location (auto-switches regions if needed).

**Emit:**
```javascript
socket.emit('update-location', {
  latitude: 28.6150,
  longitude: 77.2100
});
```

**Receive (if region changed):**
```javascript
socket.on('region-changed', (data) => {
  console.log(data);
  // {
  //   oldRegion: 'ttnkbz',
  //   newRegion: 'ttnkc0',
  //   timestamp: '2026-01-18T10:35:00Z'
  // }
});
```

---

#### 4. ping
Heartbeat to keep connection alive.

**Emit:**
```javascript
socket.emit('ping');
```

**Receive:**
```javascript
socket.on('pong', (data) => {
  console.log(data);
  // { timestamp: '2026-01-18T10:30:00Z' }
});
```

---

### Server → Client Events

#### 1. road-quality-update
Broadcast when road quality is updated in your region.

**Receive:**
```javascript
socket.on('road-quality-update', (data) => {
  console.log('Road quality updated:', data);
  // {
  //   roadSegmentId: 'seg_286139_772090',
  //   aggregatedQualityScore: 1.92,
  //   confidenceScore: 0.82,
  //   regionId: 'ttnkbz',
  //   lastUpdated: '2026-01-18T10:30:00Z'
  // }
  
  // Update map UI here
});
```

---

#### 2. user-joined-region
Notifies when another user joins your region.

**Receive:**
```javascript
socket.on('user-joined-region', (data) => {
  console.log('User joined:', data);
  // {
  //   userId: '507f1f77bcf86cd799439011',
  //   regionId: 'ttnkbz',
  //   timestamp: '2026-01-18T10:30:00Z'
  // }
});
```

---

#### 3. user-left-region
Notifies when a user leaves your region.

**Receive:**
```javascript
socket.on('user-left-region', (data) => {
  console.log('User left:', data);
  // {
  //   userId: '507f1f77bcf86cd799439011',
  //   regionId: 'ttnkbz',
  //   timestamp: '2026-01-18T10:35:00Z'
  // }
});
```

---

#### 4. error
Error notifications.

**Receive:**
```javascript
socket.on('error', (data) => {
  console.error('Socket error:', data);
  // { message: 'Invalid location data' }
});
```

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "message": "Error description",
  "errors": [
    {
      "field": "email",
      "message": "Email is required"
    }
  ]
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing or invalid token)
- `404` - Not Found
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

---

## Rate Limiting

- **Window**: 15 minutes
- **Max Requests**: 100 per IP
- **Applies to**: All `/api/*` endpoints

When rate limit is exceeded:
```json
{
  "success": false,
  "message": "Too many requests from this IP, please try again later."
}
```
