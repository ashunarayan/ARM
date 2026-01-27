import React, { useEffect, useState } from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import firebase from '@react-native-firebase/app';
import { AuthScreen } from './src/screens/AuthScreen';
import { MapScreen } from './src/screens/MapScreen';
import { AuthService } from './src/services/authService';
import { FIREBASE_CONFIG } from './src/config';

if (!firebase.apps.length) {
  firebase.initializeApp(FIREBASE_CONFIG);
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = AuthService.onAuthStateChanged((user) => {
      setIsAuthenticated(!!user);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  if (loading) {
    return null;
  }

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" />
      {isAuthenticated ? (
        <MapScreen onSignOut={() => setIsAuthenticated(false)} />
      ) : (
        <AuthScreen onAuthSuccess={() => setIsAuthenticated(true)} />
      )}
    </SafeAreaProvider>
  );
}

export default App;
