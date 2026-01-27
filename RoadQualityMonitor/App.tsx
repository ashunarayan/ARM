import React, { useEffect, useState } from 'react';
import { SafeAreaView, StatusBar, StyleSheet, ActivityIndicator, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { MapScreen } from './src/screens/MapScreen';
import { LoginScreen } from './src/screens/LoginScreen';
import { authService } from './src/services/authService';
import 'react-native-gesture-handler';

const Stack = createStackNavigator();

const App = (): React.JSX.Element => {
    const [isLoading, setIsLoading] = useState(true);
    const [initialRoute, setInitialRoute] = useState('Login');

    useEffect(() => {
        const checkAuth = async () => {
             try {
                 const token = await authService.getToken();
                 if (token) {
                     setInitialRoute('Map');
                 }
             } catch (e) {
                 console.error(e);
             } finally {
                 setIsLoading(false);
             }
        };
        checkAuth();
    }, []);

    if (isLoading) {
        return (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                <ActivityIndicator size="large" color="#0000ff" />
            </View>
        );
    }

    return (
        <NavigationContainer>
            <StatusBar barStyle="dark-content" />
            <Stack.Navigator initialRouteName={initialRoute} screenOptions={{ headerShown: false }}>
                <Stack.Screen name="Login" component={LoginScreen} />
                <Stack.Screen name="Map" component={MapScreen} />
            </Stack.Navigator>
        </NavigationContainer>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
    }
});

export default App;
