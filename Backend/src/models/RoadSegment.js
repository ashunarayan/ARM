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
      type: [[Number]], // [[lng, lat], ...]
      required: true
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

  lastUpdated: {
    type: Date
  }

}, { timestamps: true });

roadSegmentSchema.index({ geometry: "2dsphere" });
roadSegmentSchema.index({ regionId: 1 });

module.exports = mongoose.model("RoadSegment", roadSegmentSchema);
