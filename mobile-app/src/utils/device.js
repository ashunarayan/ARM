import * as Application from "expo-application";

export const getDeviceId = async () => {
  return Application.androidId ?? "unknown-device";
};
