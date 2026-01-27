import { Platform } from 'react-native';

export const FIREBASE_CONFIG = {
    apiKey: 'AIzaSyBsaCjUCh7jGDtyBdWHFC2NhVzBZ5tFhYY',
    authDomain: 'a-rm-218b9.firebaseapp.com',
    projectId: 'a-rm-218b9',
    storageBucket: 'a-rm-218b9.firebasestorage.app',
    messagingSenderId: '628690193635',
    appId: '1:628690193635:web:d6996ca234b3cde039c9d6',
};

export const BACKEND_URL = __DEV__
    ? Platform.OS === 'android' ? 'http://10.66.175.173:3000' : 'http://localhost:3000'
    : 'https://your-production-backend.com';

export const MAPBOX_ACCESS_TOKEN = 'pk.eyJ1IjoiYXNodS1zcmkiLCJhIjoiY21rdG9mNjM0MXFpZTNscW5tdGhhN212aCJ9.ODYbCtFkoMBaKakX-3sHWw';

export const APP_VERSION = '1.0.0';
