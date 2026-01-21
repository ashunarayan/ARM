import { useEffect } from "react";
import { View, Text } from "react-native";
import { initAnonymousAuth } from "../src/auth/authService";
import { sendObservation } from "../src/services/observationService";

export default function Index() {
  useEffect(() => {
    const run = async () => {
      console.log("🔥 APP STARTED");

      try {
        console.log("🔐 initAnonymousAuth()");
        await initAnonymousAuth();

        console.log("📡 sendObservation()");
        await sendObservation();

        console.log("✅ OBSERVATION SENT");
      } catch (err) {
        console.log("❌ ERROR:", err);
      }
    };

    run();
  }, []);

  return (
    <View style={{ padding: 40 }}>
      <Text>Road App Running</Text>
    </View>
  );
}
