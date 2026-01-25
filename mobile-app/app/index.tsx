// ============================================
// 🧪 TEMPORARY TEST ONLY - REMOVE AFTER TESTING
// ============================================
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { useState } from "react";
import { apiRequest } from "../src/api/client";
import { MapView } from "../src/components/MapView";
import type { MapMarker } from "../src/types";

export default function Index() {
  const [testResult, setTestResult] = useState<string>("");
  const [markers, setMarkers] = useState<MapMarker[]>([]);

  // 🧪 TEST: Send fake observation to backend
  const runEndToEndTest = async () => {
    try {
      setTestResult("⏳ Testing...");

      // FAKE TEST DATA - matches backend schema exactly
      const fakeObservations = [
        {
          latitude: 28.6139,
          longitude: 77.2090,
          roadQuality: 3, // Very Good (Green)
          speed: 12.5,
          timestamp: new Date().toISOString(),
        },
        {
          latitude: 28.6149,
          longitude: 77.2095,
          roadQuality: 1, // Bad (Orange)
          speed: 10.2,
          timestamp: new Date().toISOString(),
        },
        {
          latitude: 28.6159,
          longitude: 77.2100,
          roadQuality: 0, // Very Bad (Red)
          speed: 8.5,
          timestamp: new Date().toISOString(),
        },
      ];

      const newMarkers: MapMarker[] = [];

      // Send each fake observation
      for (const obs of fakeObservations) {
        console.log("🧪 TEST: Sending fake observation:", obs);

        const response = await apiRequest("/observations", {
          method: "POST",
          body: obs,
        });

        console.log("✅ TEST: Backend response:", response);

        // Add marker to map
        newMarkers.push({
          id: `test-${obs.roadQuality}-${Date.now()}`,
          coordinate: [obs.longitude, obs.latitude],
          quality: obs.roadQuality as 0 | 1 | 2 | 3,
          timestamp: Date.now(),
        });
      }

      setMarkers(newMarkers);
      setTestResult(`✅ TEST PASSED\n${newMarkers.length} observations sent\nCheck map colors!`);
    } catch (error) {
      console.error("❌ TEST FAILED:", error);
      setTestResult(`❌ TEST FAILED\n${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  return (
    <View style={styles.container}>
      {/* Map with test markers */}
      <MapView
        markers={markers}
        initialLocation={{ latitude: 28.6139, longitude: 77.2090, zoom: 14 }}
        showUserLocation={false}
      />

      {/* Test Control Panel */}
      <View style={styles.testPanel}>
        <Text style={styles.title}>🧪 END-TO-END TEST</Text>

        <TouchableOpacity style={styles.button} onPress={runEndToEndTest}>
          <Text style={styles.buttonText}>RUN TEST</Text>
        </TouchableOpacity>

        {testResult ? (
          <View style={styles.result}>
            <Text style={styles.resultText}>{testResult}</Text>
          </View>
        ) : null}

        <Text style={styles.legend}>
          🟢 Green = Very Good (3){"\n"}
          🟡 Yellow = Good (2){"\n"}
          🟠 Orange = Bad (1){"\n"}
          🔴 Red = Very Bad (0)
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  testPanel: {
    position: "absolute",
    top: 50,
    left: 20,
    right: 20,
    backgroundColor: "white",
    borderRadius: 12,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 5,
  },
  title: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 12,
    textAlign: "center",
  },
  button: {
    backgroundColor: "#007AFF",
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
  },
  buttonText: {
    color: "white",
    fontSize: 16,
    fontWeight: "bold",
    textAlign: "center",
  },
  result: {
    backgroundColor: "#F0F0F0",
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  resultText: {
    fontSize: 14,
    textAlign: "center",
  },
  legend: {
    fontSize: 12,
    color: "#666",
    textAlign: "center",
  },
});
// ============================================
// 🧪 END TEST CODE - REMOVE AFTER TESTING
// ============================================
