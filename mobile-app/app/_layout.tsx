import { Stack } from "expo-router";
import { useEffect, useState } from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { initAuth } from "../src/services/auth";
import { initializeApp } from "../src/services/appInitializer";

export default function Layout() {
  const [isInitializing, setIsInitializing] = useState(true);
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    const initialize = async () => {
      try {
        // Initialize auth
        await initAuth();
        console.log("🔐 Auth ready");

        // Initialize app services (Mapbox, ML)
        const status = await initializeApp();

        if (status.errors.length > 0) {
          console.warn("⚠️  Some services failed to initialize:", status.errors);
          // Continue even with some errors
        }
      } catch (error) {
        console.error("❌ Initialization failed:", error);
        setInitError(error instanceof Error ? error.message : "Unknown error");
      } finally {
        setIsInitializing(false);
      }
    };

    initialize();
  }, []);

  if (isInitializing) {
    return (
      <View style={styles.initContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.initText}>Initializing app...</Text>
      </View>
    );
  }

  if (initError) {
    return (
      <View style={styles.initContainer}>
        <Text style={styles.errorText}>⚠️  Initialization Error</Text>
        <Text style={styles.errorMessage}>{initError}</Text>
      </View>
    );
  }

  return <Stack />;
}

const styles = StyleSheet.create({
  initContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#fff",
  },
  initText: {
    marginTop: 12,
    fontSize: 16,
    color: "#666",
  },
  errorText: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#FF3B30",
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 14,
    color: "#666",
    textAlign: "center",
    paddingHorizontal: 32,
  },
});
