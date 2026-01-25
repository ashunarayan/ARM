const admin = require('firebase-admin');

let firebaseInitialized = false;

const initializeFirebase = () => {
    if (firebaseInitialized) return;

    admin.initializeApp({
        credential: admin.credential.cert({
            projectId: process.env.FIREBASE_PROJECT_ID,
            clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
            privateKey: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
        }),
    });

    firebaseInitialized = true;
};

const verifyFirebaseToken = async (token) => {
    if (!firebaseInitialized) {
        initializeFirebase();
    }
    return admin.auth().verifyIdToken(token);
};

module.exports = { initializeFirebase, verifyFirebaseToken };
