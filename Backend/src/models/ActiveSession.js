const mongoose = require("mongoose");

const activeSessionSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "User",
    required: true
  },

  socketId: {
    type: String,
    required: true,
    unique: true
  },

  currentRegionId: String,

  lastLocation: {
    latitude: Number,
    longitude: Number
  },

  lastActivityAt: {
    type: Date,
    default: Date.now,
    index: { expires: "1h" }
  }

}, { timestamps: true });

module.exports = mongoose.model("ActiveSession", activeSessionSchema);
