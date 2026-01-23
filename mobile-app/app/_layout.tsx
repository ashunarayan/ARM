import { Stack } from "expo-router";
import { useEffect } from "react";
import { initAuth } from "../src/services/auth";

export default function Layout() {
  useEffect(() => {
    initAuth()
      .then(() => console.log(" Auth ready"))
      .catch(err => console.log(" Auth failed", err));
  }, []);

  return <Stack />;
}
