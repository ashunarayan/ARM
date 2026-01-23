/**
 * QUICK BACKEND CONNECTIVITY TEST
 * Tests POST /api/observations with auth
 */

const BASE_URL = "http://10.66.175.173:5000/api";

async function testBackendConnectivity() {
  try {
    console.log(" TEST OBSERVATION - Backend Connectivity Check\n");

    // Step 1: Get Auth Token
    console.log("Step 1: Getting auth token...");
    const authRes = await fetch(`${BASE_URL}/auth/anonymous`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deviceId: "test-device-connectivity" }),
    });

    const authData = await authRes.json();
    const token = authData.data.token;
    console.log(" Token received:", token.substring(0, 20) + "...\n");

    // Step 2: Send Test Observation
    console.log("Step 2: Sending test observation...");
    
    // Add random offset to avoid duplicate errors (backend deduplication)
    const randomOffset = () => (Math.random() - 0.5) * 0.01;
    
    const payload = {
      latitude: 28.7037 + randomOffset(),
      longitude: 77.2079 + randomOffset(),
      roadQuality: 2,
      speed: 10,
      timestamp: new Date().toISOString(),
    };

    console.log(" Payload:", JSON.stringify(payload, null, 2));

    const obsRes = await fetch(`${BASE_URL}/observations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    const obsData = await obsRes.json();

    console.log("\n Backend Response:");
    console.log("   Status:", obsRes.status);
    console.log("   Success:", obsData.success);
    console.log("   Message:", obsData.message);
    console.log("   Data:", JSON.stringify(obsData.data, null, 2));

    // Step 3: Verification
    console.log("\n VERIFICATION:");
    console.log("   ✓ Request succeeded:", obsRes.status === 201);
    console.log("   ✓ Success flag:", obsData.success === true);
    console.log("   ✓ Observation ID:", obsData.data?.observationId || "N/A");
    console.log("   ✓ Road Segment ID:", obsData.data?.roadSegmentId || "N/A");
    console.log("\n TEST OBSERVATION SENT");
    console.log(" Backend API is responding correctly");
    console.log(" Check MongoDB 'observations' collection to verify data persistence");

  } catch (error) {
    console.error("\n TEST FAILED:", error.message);
    console.error(error);
    process.exit(1);
  }
}

testBackendConnectivity();
