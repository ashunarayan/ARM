/**
 * API Client
 * Centralized HTTP client for backend communication
 * 
 * ARCHITECTURE:
 * - Handles authentication tokens
 * - Provides generic request methods
 * - Error handling and logging
 * - Timeout configuration
 * - Isolated from ML and map logic
 */

import { ENV } from '../config/env';
import { getIdToken } from '../services/firebaseAuth';

let authToken: string | null = null;

export const setAuthToken = (token: string | null): void => {
    authToken = token;
};

export const getAuthToken = (): string | null => {
    return authToken;
};

interface RequestOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    body?: any;
    headers?: Record<string, string>;
    timeout?: number;
}

/**
 * Make an API request
 */
export const apiRequest = async <T = any>(
    endpoint: string,
    options: RequestOptions = {}
): Promise<T> => {
    const { method = 'GET', body, headers = {}, timeout = ENV.API.TIMEOUT } = options;

    const url = `${ENV.API.BASE_URL}${endpoint}`;

    if (ENV.FEATURES.ENABLE_DEBUG_LOGGING) {
        console.log(' API REQUEST');
        console.log(' URL:', url);
        console.log(' METHOD:', method);
        console.log(' BODY:', body);
    }

    const token = await getIdToken();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
                ...headers,
            },
            body: body ? JSON.stringify(body) : undefined,
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        const data = await response.json();

        if (ENV.FEATURES.ENABLE_DEBUG_LOGGING) {
            console.log(' RESPONSE STATUS:', response.status);
            console.log(' RESPONSE DATA:', data);
        }

        if (!response.ok) {
            throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        return data;
    } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof Error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            console.error(' API REQUEST FAILED:', error.message);
            throw error;
        }

        throw new Error('Unknown error occurred');
    }
};
