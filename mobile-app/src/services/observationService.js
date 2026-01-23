import { apiRequest } from "../api/apiClient";
import { getCurrentLocation } from "./locationService";
import { getRoadQualityFromML } from "./mlService";

export const sendObservation = async () => {
  console.log(" sendObservation() CALLED");

  const location = await getCurrentLocation();
  const roadQuality = await getRoadQualityFromML();

  const payload = {
    latitude: location.latitude,
    longitude: location.longitude,
    roadQuality,
    speed: location.speed ?? 0,
    timestamp: new Date().toISOString(),
  };

  console.log(" Payload:", payload);

  await apiRequest("/observations", "POST", payload);

  console.log(" Observation SENT");
};
