import AsyncStorage from '@react-native-async-storage/async-storage';
import { ENV } from '../config/env';

const TOKEN_KEY = 'auth_token';

export const authService = {
  async login(email, password) {
    try {
      const response = await fetch(`${ENV.API.BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(responseData.message || 'Login failed');
      }

      const token = responseData.data?.token;
      if (!token) throw new Error('No token received from server');
      
      await this.setToken(token);
      return token;
    } catch (error) {
      console.error('Login Error:', error);
      throw error;
    }
  },

  async anonymousLogin() {
     try {
        const response = await fetch(`${ENV.API.BASE_URL}/api/auth/anonymous`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ deviceId: 'mobile-app-' + Date.now() })
        });
        
        const responseData = await response.json();
        if (!response.ok) throw new Error(responseData.message || 'Anonymous login failed');

        const token = responseData.data?.token;
        if (!token) throw new Error('No token received from server');

        await this.setToken(token);
        return token;
     } catch (error) {
         console.error('Anon Login Error:', error);
         throw error;
     }
  },

  async setToken(token) {
    await AsyncStorage.setItem(TOKEN_KEY, token);
  },

  async getToken() {
    return await AsyncStorage.getItem(TOKEN_KEY);
  },

  async logout() {
    await AsyncStorage.removeItem(TOKEN_KEY);
  },
};
