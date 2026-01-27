import { io, Socket } from 'socket.io-client';
import { Platform } from 'react-native';

class SocketService {
    private socket: Socket | null = null;
    private isConnected: boolean = false;
    private listeners: Record<string, Function[]> = {};

    connect(url: string, auth: object = {}) {
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
            console.log('Socket connected:', this.socket?.id);
            this.isConnected = true;
            this.notifyListeners('connect', null);
        });

        this.socket.on('disconnect', () => {
            console.log('Socket disconnected');
            this.isConnected = false;
            this.notifyListeners('disconnect', null);
        });

        this.socket.on('road-quality-update', (data: any) => {
            this.notifyListeners('road-quality-update', data);
        });
    }

    sendRoadQualityUpdate(quality: number, location: { latitude: number; longitude: number }) {
        if (!this.isConnected || !this.socket) return;
        this.socket.emit('road-quality-update', {
            quality,
            location,
            timestamp: Date.now()
        });
    }

    on(event: string, callback: Function) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    off(event: string, callback: Function) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }

    private notifyListeners(event: string, data: any) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => cb(data));
        }
    }
}

export const socketService = new SocketService();
