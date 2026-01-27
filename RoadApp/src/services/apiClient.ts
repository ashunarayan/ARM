import axios, { AxiosInstance } from 'axios';
import { BACKEND_URL } from '../config';
import { AuthService } from './authService';

class ApiClient {
    private instance: AxiosInstance;

    constructor() {
        this.instance = axios.create({
            baseURL: BACKEND_URL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        this.instance.interceptors.request.use(
            async (config) => {
                const token = await AuthService.getToken();
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );
    }

    getAxiosInstance(): AxiosInstance {
        return this.instance;
    }
}

export const apiClient = new ApiClient().getAxiosInstance();
