import { View, Text } from "react-native";
import { useEffect } from "react";
import { sendObservation } from "../src/services/observationService";

export default function Index() {
  useEffect(() => {
    sendObservation();
  }, []);

  return (
    <View style={{ padding: 40 }}>
      <Text>Road App Running</Text>
    </View>
  );
}
