# Data Flow Diagram

## Complete Pipeline: Sensors → Backend

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MOBILE APP (On-Device)                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│ Device Sensors  │ ← Accelerometer, Gyroscope, GPS
│   @ 10 Hz       │
└────────┬────────┘
         │ Every 100ms
         │ {ax, ay, az, wx, wy, wz, speed, location}
         ▼
┌─────────────────┐
│ Sensor Collector│ ← sensorService.js
│ (Buffer Latest) │
└────────┬────────┘
         │ Samples at 10 Hz
         │
         ▼
┌─────────────────┐
│ Window Manager  │ ← windowService.js
│ (20 readings)   │
└────────┬────────┘
         │ Every 2 seconds (when buffer full)
         │ Produces 20x7 sensor matrix
         │
         ▼
┌─────────────────┐
│ TFLite Model    │ ← tfliteService.js
│  Inference      │   Input: [1, 20, 7] tensor
│  @ ~50ms        │   Output: roadQuality (0-3)
└────────┬────────┘
         │ Result with metadata
         │ {roadQuality, lat, lng, speed, timestamp}
         ▼
┌─────────────────┐
│  ML Service     │ ← mlService.js
│ (Latest Result) │   Stores most recent classification
└────────┬────────┘
         │
         │ Check every 2 seconds
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OBSERVATION MANAGER (Intelligence)                       │
│                                                                             │
│  Decision Logic:                                                            │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │ IF roadQuality changed         → SEND                         │          │
│  │ OR distance > 25m              → SEND                         │          │
│  │ OR time > 12s (while moving)   → SEND                         │          │
│  │ OR time > 30s (force)          → SEND                         │          │
│  │ ELSE                           → SKIP                         │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  Statistics Tracking:                                                       │
│  - Total inferences: 150                                                    │
│  - Total sent: 45                                                           │
│  - Efficiency: 70%                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         │ Only meaningful observations
         ▼
┌─────────────────┐
│Observation Svc  │ ← observationService.js
│  (API Client)   │
└────────┬────────┘
         │ HTTP POST /api/observations
         │ Authorization: Bearer <token>
         │ Content-Type: application/json
         │
         │ Payload (ONLY 5 fields):
         │ {
         │   latitude: 40.7128,
         │   longitude: -74.0060,
         │   roadQuality: 2,
         │   speed: 15.5,
         │   timestamp: "2026-01-23T12:34:56Z"
         │ }
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (Server-Side)                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   Validation    │ ← middleware/validation.js
│   Middleware    │   Validates 5 required fields
└────────┬────────┘
         │ req.validatedData
         ▼
┌─────────────────┐
│  Map Matching   │ ← services/mapMatching.js
│    Service      │   Matches GPS to road network
└────────┬────────┘
         │ roadSegmentId, matchedLocation
         ▼
┌─────────────────┐
│  Create Record  │ ← models/Observation.js
│  Observation    │   Store in MongoDB
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Update Road    │ ← models/RoadSegment.js
│    Segment      │   Update segment metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Aggregation    │ ← services/aggregation.js
│    Service      │   Calculate average quality
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Socket.IO      │ ← socket/index.js
│   Broadcast     │   Notify connected clients
└─────────────────┘
         │
         ▼
   [Real-time Map Updates]
```

---

## Timeline Example: 10 Second Window

```
Time  | Sensor | Window | Inference | Manager Decision        | Backend
------|--------|--------|-----------|-------------------------|----------
0.0s  | ✓      |        |           |                         |
0.1s  | ✓      |        |           |                         |
0.2s  | ✓      |        |           |                         |
...   | ...    |        |           |                         |
2.0s  | ✓      | READY  | Q=2       | ✅ SEND (first)         | ✅ Stored
2.1s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 3m)      |
2.2s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 6m)      |
2.3s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 9m)      |
2.4s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 12m)     |
2.5s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 15m)     |
2.6s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 18m)     |
2.7s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 21m)     |
2.8s  | ✓      | READY  | Q=2       | ⏭️ SKIP (same, 24m)     |
2.9s  | ✓      | READY  | Q=2       | ✅ SEND (distance>25m)  | ✅ Stored
3.0s  | ✓      | READY  | Q=1       | ✅ SEND (quality changed)| ✅ Stored
```

**Result**: 3 observations sent instead of 15  
**Efficiency**: 80% reduction  
**Data Quality**: All meaningful changes captured

---

## Data Size Comparison

### Per Observation

**Raw Sensor Window (NOT sent)**:
```
20 readings × 7 values × 8 bytes = 1,120 bytes
+ metadata = ~1,200 bytes
```

**Actual Payload (sent)**:
```json
{
  "latitude": 40.7128,           // 8 bytes
  "longitude": -74.0060,         // 8 bytes
  "roadQuality": 2,              // 4 bytes
  "speed": 15.5,                 // 8 bytes
  "timestamp": "2026-01-23..."   // ~25 bytes
}
Total: ~150 bytes (as JSON)
```

**Compression**: 88% smaller payload

### Per Minute

**Without Intelligent Filtering**:
- Inferences: 30
- Observations sent: 30
- Data transferred: 30 × 150 = 4.5 KB/min

**With Intelligent Filtering**:
- Inferences: 30
- Observations sent: 2-8 (avg: 5)
- Data transferred: 5 × 150 = 750 bytes/min

**Savings**: 83% reduction in network usage

---

## Quality Transition Capture

### Example: 2km Mixed Road

```
Segment | Quality | Distance | Decision      | Sent?
--------|---------|----------|---------------|-------
0-100m  | Good(2) | 0m       | First         | ✅
100-200m| Good(2) | 100m     | Distance>25m  | ✅ (4x)
200-250m| Bad(1)  | 250m     | Quality change| ✅
250-350m| Bad(1)  | 300m     | Distance>25m  | ✅ (4x)
350-400m| Good(2) | 400m     | Quality change| ✅
...     | ...     | ...      | ...           | ...
```

**Total**: 2km road  
**Observations**: ~30 (instead of 100 every 20m)  
**Quality transitions**: 100% captured  
**Map visualization**: Perfect

---

## Map Rendering Flow

```
Backend
  ↓
Aggregated Road Segments
  {
    roadSegmentId: "seg_123",
    aggregatedQualityScore: 2.3,
    geometry: LineString,
    observationCount: 15
  }
  ↓
Frontend Map Component
  ↓
Color-Coded Polylines
  - Very Bad (0-0.75): Red (#DC2626)
  - Bad (0.75-1.75): Orange (#F59E0B)
  - Good (1.75-2.75): Yellow (#FCD34D)
  - Very Good (2.75-3): Green (#10B981)
  ↓
Interactive Map with Quality Overlay
```

---

## Mobile App Services Interaction

```
┌──────────────────────────────────────────────────────────────┐
│                      App Lifecycle                           │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ ML Service   │ ← Main orchestrator
                    │ .initialize()│
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌────────────────┐ ┌──────────────┐ ┌──────────────┐
│ Sensor Service │ │ Window Mgr   │ │ TFLite Svc   │
│ .start()       │ │ .initialize()│ │ .loadModel() │
└───────┬────────┘ └──────┬───────┘ └──────┬───────┘
        │                 │                 │
        │ readings        │ windows         │ inference
        └────────►────────┴────────►────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Latest Result  │
                  │ Storage        │
                  └────────┬───────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Observation    │
                  │ Manager        │
                  │ (Smart Filter) │
                  └────────┬───────┘
                           │
                      YES  │  NO
                   ┌───────┴───────┐
                   ▼               ▼
           ┌──────────────┐  ┌──────────┐
           │ API Request  │  │   Skip   │
           │ Send to      │  │   Log    │
           │ Backend      │  │  Stats   │
           └──────────────┘  └──────────┘
```

---

## Error Handling Flow

```
┌──────────────────┐
│  Sensor Error    │ → Log + Alert User
└──────────────────┘

┌──────────────────┐
│  Model Error     │ → Fallback to Mock Inference
└──────────────────┘

┌──────────────────┐
│  Network Error   │ → Log + Retry (handled by apiClient)
└──────────────────┘

┌──────────────────┐
│  Validation Error│ → Log + Skip (invalid data)
└──────────────────┘

┌──────────────────┐
│  Location Error  │ → Log + Use last known location
└──────────────────┘
```

All errors logged with emojis for easy console filtering:
- ✅ Success
- ⚠️ Warning
- ❌ Error
- 🔮 Inference
- 📤 Network

---

**This diagram shows the complete data flow from device sensors to backend storage,
highlighting the intelligent filtering that prevents spam while ensuring map-ready data.**
