# Folder Structure

```
Road/
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Example environment configuration
├── .gitignore                    # Git ignore rules
├── package.json                  # Node.js dependencies and scripts
├── README.md                     # Project overview and quick start
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # System architecture and data flow
│   ├── API.md                    # REST API and WebSocket documentation
│   ├── DATABASE_SCHEMA.md        # MongoDB schema design
│   ├── DEPLOYMENT.md             # Production deployment guide
│   └── SOCKET_IO_ROOMS.md        # Socket.IO room logic explained
│
└── src/                          # Source code
    ├── server.js                 # Main application entry point
    │
    ├── config/                   # Configuration files
    │   └── database.js           # MongoDB connection setup
    │
    ├── models/                   # MongoDB schemas (Mongoose)
    │   ├── User.js               # User authentication and profiles
    │   ├── Observation.js        # Raw road quality observations
    │   ├── RoadSegment.js        # Aggregated road quality data
    │   └── ActiveSession.js      # Socket.IO session tracking
    │
    ├── controllers/              # Request handlers
    │   ├── authController.js     # Register, login, anonymous auth
    │   ├── observationController.js  # Submit observations, history
    │   └── roadController.js     # Get road segments, statistics
    │
    ├── routes/                   # API route definitions
    │   ├── index.js              # Route aggregator
    │   ├── auth.js               # /api/auth routes
    │   ├── observations.js       # /api/observations routes
    │   └── roads.js              # /api/roads routes
    │
    ├── middleware/               # Express middleware
    │   ├── auth.js               # JWT authentication for REST API
    │   ├── socketAuth.js         # JWT authentication for Socket.IO
    │   ├── validation.js         # Request validation (Joi schemas)
    │   └── errorHandler.js       # Global error handling
    │
    ├── services/                 # Business logic services
    │   ├── mapMatching.js        # OSRM map matching integration
    │   └── aggregation.js        # Road quality aggregation logic
    │
    ├── socket/                   # Socket.IO server
    │   └── index.js              # Real-time server and room logic
    │
    └── utils/                    # Utility functions
        ├── jwt.js                # JWT token generation/verification
        └── geohash.js            # Geohash calculation and utilities
```

---

## File Descriptions

### Root Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (MongoDB URI, JWT secret, etc.) |
| `.env.example` | Template for environment configuration |
| `.gitignore` | Excludes node_modules, .env, logs from git |
| `package.json` | Dependencies, scripts, project metadata |
| `README.md` | Project overview, installation, quick start |

---

### `/docs` - Documentation

| File | Content |
|------|---------|
| `ARCHITECTURE.md` | System architecture diagrams, data flow, scalability |
| `API.md` | Complete REST API and WebSocket event documentation |
| `DATABASE_SCHEMA.md` | MongoDB collections, indexes, query examples |
| `DEPLOYMENT.md` | Production deployment guide (VPS, Docker, Heroku) |
| `SOCKET_IO_ROOMS.md` | Socket.IO room logic, geohash regionalization |

---

### `/src` - Source Code

#### Core Files

| File | Responsibility |
|------|----------------|
| `server.js` | Express app setup, middleware, start HTTP server |

#### `/config`

| File | Purpose |
|------|---------|
| `database.js` | MongoDB connection with Mongoose, error handling |

#### `/models` - Data Models

| File | Schema |
|------|--------|
| `User.js` | Users, authentication, anonymous users |
| `Observation.js` | Raw road quality observations from mobile |
| `RoadSegment.js` | Aggregated road quality per segment |
| `ActiveSession.js` | Socket.IO connection tracking (TTL) |

#### `/controllers` - Request Handlers

| File | Handles |
|------|---------|
| `authController.js` | Register, login, anonymous auth, profile |
| `observationController.js` | Submit observations, get history |
| `roadController.js` | Get road segments, nearby roads, statistics |

#### `/routes` - API Routes

| File | Routes |
|------|--------|
| `index.js` | Route aggregator, health check |
| `auth.js` | POST /api/auth/register, /login, /anonymous |
| `observations.js` | POST /api/observations, GET /history |
| `roads.js` | GET /api/roads/region/:id, /nearby, /stats |

#### `/middleware`

| File | Purpose |
|------|---------|
| `auth.js` | JWT authentication for REST API |
| `socketAuth.js` | JWT authentication for Socket.IO |
| `validation.js` | Request body validation (Joi) |
| `errorHandler.js` | Global error handling, 404 handler |

#### `/services` - Business Logic

| File | Responsibility |
|------|----------------|
| `mapMatching.js` | OSRM API integration, GPS → road matching |
| `aggregation.js` | Weighted average, time decay, quality scoring |

#### `/socket`

| File | Purpose |
|------|---------|
| `index.js` | Socket.IO server, room management, events |

#### `/utils` - Utilities

| File | Functions |
|------|-----------|
| `jwt.js` | Generate and verify JWT tokens |
| `geohash.js` | Geohash encoding, neighbors, distance calculation |

---

## Key Design Patterns

### 1. **MVC-like Structure**
```
Request → Route → Controller → Service → Model → Database
                                    ↓
                              Response
```

### 2. **Middleware Chain**
```
Request → CORS → Helmet → Body Parser → Rate Limit 
       → Auth → Validation → Controller → Response
```

### 3. **Socket.IO Flow**
```
Client Connection → Socket Auth Middleware → Event Handlers
                                                  ↓
                                            Room Management
                                                  ↓
                                              Broadcast
```

### 4. **Service Layer**
Separates business logic from controllers:
- `mapMatching.js`: External API integration
- `aggregation.js`: Complex calculations

### 5. **Error Handling**
All errors flow to `errorHandler.js` middleware:
```javascript
try {
  // Controller logic
} catch (error) {
  next(error);  // Handled by errorHandler middleware
}
```

---

## Adding New Features

### Add a new REST endpoint:

1. **Create controller** in `/controllers/newController.js`
2. **Create route** in `/routes/new.js`
3. **Import in** `/routes/index.js`
4. **Add validation** in `/middleware/validation.js` (if needed)

### Add a new Socket.IO event:

1. **Edit** `/socket/index.js`
2. Add event handler in `io.on('connection', ...)` block

### Add a new model:

1. **Create schema** in `/models/NewModel.js`
2. **Add indexes** for performance
3. **Import in controllers** as needed

---

## Scripts

```json
{
  "start": "node src/server.js",        // Production
  "dev": "nodemon src/server.js",       // Development with auto-reload
  "test": "jest --coverage"             // Run tests
}
```

---

This structure ensures:
- ✅ **Separation of concerns** (routes, controllers, services, models)
- ✅ **Scalability** (easy to add features)
- ✅ **Maintainability** (clear file organization)
- ✅ **Testability** (isolated business logic)
