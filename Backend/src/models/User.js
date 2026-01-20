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
    required: true,
    unique: true
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

userSchema.index({ email: 1 });
userSchema.index({ deviceId: 1 });
userSchema.index({ lastActive: -1 });

module.exports = mongoose.model("User", userSchema);
