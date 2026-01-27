import { io } from 'socket.io-client';
import { Platform } from 'react-native';

class SocketService {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.listeners = {};
    }

    /**
     * Initialize connection to Backend
     * @param {string} url - Backend URL
     * @param {object} auth - Authentication object { userId }
     */
    connect(url, auth = {}) {
        if (this.socket) {
            this.socket.disconnect();
        }

        console.log('Connecting to socket:', url);

        this.socket = io(url, {
            transports: ['websocket'],
            auth: auth,
            query: {
                platform: Platform.OS
            }
        });

        this.socket.on('connect', () => {
            console.log('Socket connected:', this.socket.id);
            this.isConnected = true;
            this.notifyListeners('connect');
        });

        this.socket.on('disconnect', () => {
            console.log('Socket disconnected');
            this.isConnected = false;
            this.notifyListeners('disconnect');
        });

        this.socket.on('error', (err) => {
            console.error('Socket error:', err);
            this.notifyListeners('error', err);
        });

        // Listen for region events
        this.socket.on('region-joined', (data) => {
            console.log('Region joined:', data);
        });

        // Listen for road quality updates from other users
        this.socket.on('road-quality-update', (data) => {
            // data: { userId, location: { lat, lng }, quality, timestamp }
            this.notifyListeners('road-quality-update', data);
        });
    }

    /**
     * Send road quality update
     * @param {number} quality - 0: Good, 1: Average, 2: Bad, 3: Very Bad
     * @param {object} location - { latitude, longitude }
     */
    sendRoadQualityUpdate(quality, location) {
        if (!this.isConnected || !this.socket) return;

        this.socket.emit('road-quality-update', {
            quality,
            location,
            timestamp: Date.now()
        });
    }

    /**
     * Update user location (for region tracking)
     * @param {object} location - { latitude, longitude }
     */
    updateLocation(location) {
        if (!this.isConnected || !this.socket) return;

        this.socket.emit('update-location', location);
    }

    joinRegion(location) {
        if (!this.isConnected || !this.socket) return;
        this.socket.emit('join-region', location);
    }

    // Event Listener Management
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }

    notifyListeners(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => cb(data));
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
            this.isConnected = false;
        }
    }
}

export const socketService = new SocketService();
