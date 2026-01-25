import * as SecureStore from "expo-secure-store";
import { setAuthToken } from "../api/client";

const API = "http://10.66.175.173:5000/api";

export async function initAuth() {
  console.log(" INIT AUTH START");

  let token = await SecureStore.getItemAsync("token");

  if (!token) {
    const res = await fetch(`${API}/auth/anonymous`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deviceId: "mobile-device" }),
    });

    const json = await res.json();
    token = json.data.token;

    await SecureStore.setItemAsync("token", token);
    console.log(" Token stored");
  }

  setAuthToken(token);
  console.log(" Token set in apiClient");
}
