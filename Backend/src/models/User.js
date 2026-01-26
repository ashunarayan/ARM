const mongoose = require("mongoose");

const userSchema = new mongoose.Schema({
  email: {
    type: String,
    unique: true,
    sparse: true
  },
  password: {
    type: String,
    select: false
  },
  name: String,
  deviceId: {
    type: String,
    unique: true,
    sparse: true
  },
  firebaseUid: {
    type: String,
    unique: true,
    sparse: true
  },
  isAnonymous: {
    type: Boolean,
    default: true
  },
  lastActive: {
    type: Date,
    default: Date.now
  }
}, { timestamps: true });

// Keep only lastActive index (others defined via unique:true in schema)
userSchema.index({ lastActive: -1 });

module.exports = mongoose.model("User", userSchema);
