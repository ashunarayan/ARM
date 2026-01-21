import { apiRequest } from "../api/apiClient";
import { getCurrentLocation } from "./locationService";
import { getRoadQualityFromML } from "./mlService";

export const sendObservation = async () => {
  console.log("🚀 sendObservation() CALLED");

  try {
    const location = await getCurrentLocation();
    console.log("📍 Location:", location);

    const roadQuality = await getRoadQualityFromML();
    console.log("🧠 Road Quality:", roadQuality);

    const payload = {
      latitude: location.latitude,
      longitude: location.longitude,
      roadQuality,
      timestamp: new Date().toISOString(),
    };

    console.log("📦 Payload:", payload);

    await apiRequest("/observations", "POST", payload);

    console.log("✅ Observation SENT SUCCESSFULLY");
  } catch (err) {
    console.log("❌ sendObservation FAILED:", err.message);
  }
};

