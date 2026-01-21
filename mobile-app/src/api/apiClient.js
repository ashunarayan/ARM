import { CONFIG } from "../config/config";

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token;
};

export const apiRequest = async (endpoint, method = "GET", body) => {
  const url = `${CONFIG.BASE_URL}${endpoint}`;

  console.log("🌐 API REQUEST");
  console.log("➡️ URL:", url);
  console.log("➡️ METHOD:", method);
  console.log("➡️ BODY:", body);
  console.log("➡️ TOKEN:", authToken);

  try {
    const res = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await res.json();

    console.log("⬅️ API RESPONSE STATUS:", res.status);
    console.log("⬅️ API RESPONSE DATA:", data);

    if (!res.ok) {
      throw new Error(data.message || "API Error");
    }

    return data;
  } catch (err) {
    console.log("❌ API REQUEST FAILED:", err.message);
    throw err;
  }
};
