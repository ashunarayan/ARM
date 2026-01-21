const mongoose = require("mongoose");

const roadSegmentSchema = new mongoose.Schema({
  roadSegmentId: {
    type: String,
    required: true,
    unique: true
  },

  geometry: {
    type: {
      type: String,
      enum: ["LineString"],
      default: "LineString"
    },
    coordinates: {
      type: [[Number]],
      required: true
    }
  },

  centerPoint: {
    type: {
      type: String,
      enum: ["Point"],
      default: "Point"
    },
    coordinates: {
      type: [Number] // [lng, lat]
    }
  },

  aggregatedQualityScore: {
    type: Number,
    min: 0,
    max: 3,
    default: null
  },

  observationCount: {
    type: Number,
    default: 0
  },

  regionId: {
    type: String,
    required: true,
    index: true
  },

  lastUpdated: Date

}, { timestamps: true });

roadSegmentSchema.index({ centerPoint: "2dsphere" });
roadSegmentSchema.index({ regionId: 1 });

module.exports = mongoose.model("RoadSegment", roadSegmentSchema);
