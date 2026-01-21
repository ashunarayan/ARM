import { apiRequest } from "../api/apiClient";
import { getDeviceId } from "../utils/device";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { setAuthToken } from "../api/apiClient";

export const initAnonymousAuth = async () => {
  const storedToken = await AsyncStorage.getItem("token");

  if (storedToken) {
    setAuthToken(storedToken);
    return;
  }

  const deviceId = await getDeviceId();

  const response = await apiRequest("/auth/anonymous", "POST", {
    deviceId,
  });

  const token = response.data.token;

  await AsyncStorage.setItem("token", token);
  setAuthToken(token);
  console.log("AUTH TOKEN SET 👉", token);

};
