import React from 'react';
import { SafeAreaView, StatusBar, StyleSheet } from 'react-native';
import { MapScreen } from './src/screens/MapScreen';
import { ENV } from './src/config/env';

// Initialize services early if needed, or rely on Screen useEffect
// Here we just render the main screen
const App = (): React.JSX.Element => {
    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="dark-content" />
            <MapScreen />
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
    }
});

export default App;
