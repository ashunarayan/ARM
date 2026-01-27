import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_KEY = '@firebase_token';

export class AuthService {
    static async signUp(email: string, password: string): Promise<FirebaseAuthTypes.UserCredential> {
        const userCredential = await auth().createUserWithEmailAndPassword(email, password);
        await this.storeToken(userCredential.user);
        return userCredential;
    }

    static async signIn(email: string, password: string): Promise<FirebaseAuthTypes.UserCredential> {
        const userCredential = await auth().signInWithEmailAndPassword(email, password);
        await this.storeToken(userCredential.user);
        return userCredential;
    }

    static async signOut(): Promise<void> {
        await auth().signOut();
        await AsyncStorage.removeItem(TOKEN_KEY);
    }

    static async getToken(): Promise<string | null> {
        const user = auth().currentUser;
        if (!user) return null;

        const token = await user.getIdToken(true);
        await AsyncStorage.setItem(TOKEN_KEY, token);
        return token;
    }

    static getCurrentUser(): FirebaseAuthTypes.User | null {
        return auth().currentUser;
    }

    static onAuthStateChanged(callback: (user: FirebaseAuthTypes.User | null) => void) {
        return auth().onAuthStateChanged(callback);
    }

    private static async storeToken(user: FirebaseAuthTypes.User): Promise<void> {
        const token = await user.getIdToken();
        await AsyncStorage.setItem(TOKEN_KEY, token);
    }
}
