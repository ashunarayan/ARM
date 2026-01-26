const mongoose = require("mongoose");

const observationSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "User",
    required: true,
    index: true
  },

  location: {
    type: {
      type: String,
      enum: ["Point"],
      default: "Point"
    },
    coordinates: {
      type: [Number], // [lng, lat]
      required: true
    }
  },

  roadQuality: {
    type: Number,
    enum: [0, 1, 2, 3],
    required: true
  },

  speed: {
    type: Number // km/h (optional but useful)
  },

  matchingConfidence: {
    type: Number,
    min: 0,
    max: 1
  },

  timestamp: {
    type: Date,
    required: true,
    index: true
  },

  roadSegmentId: {
    type: String,
    required: true,
    index: true
  },

  regionId: {
    type: String,
    required: true,
    index: true
  },

  deviceMetadata: {
    model: String,
    os: String,
    appVersion: String
  }

}, { timestamps: true });

// Keep compound indexes and special indexes (individual field indexes already in schema)
observationSchema.index({ location: "2dsphere" });
observationSchema.index({ roadSegmentId: 1, timestamp: -1 });
observationSchema.index({ regionId: 1, timestamp: -1 });
observationSchema.index({ createdAt: 1 }, { expireAfterSeconds: 2592000 });

module.exports = mongoose.model("Observation", observationSchema);
