import { io, Socket } from 'socket.io-client';
import { BACKEND_URL } from '../config';

export class SocketService {
    private static socket: Socket | null = null;

    static connect(token: string): Socket {
        if (this.socket?.connected) {
            return this.socket;
        }

        this.socket = io(BACKEND_URL, {
            auth: { token },
            transports: ['websocket'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5,
        });

        this.socket.on('connect', () => {
            console.log('Socket.IO connected');
        });

        this.socket.on('disconnect', (reason) => {
            console.log('Socket.IO disconnected:', reason);
        });

        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
        });

        return this.socket;
    }

    static joinRegion(latitude: number, longitude: number): void {
        if (this.socket?.connected) {
            this.socket.emit('join-region', { latitude, longitude });
        }
    }

    static updateLocation(latitude: number, longitude: number): void {
        if (this.socket?.connected) {
            this.socket.emit('update-location', { latitude, longitude });
        }
    }

    static onRoadQualityUpdate(callback: (data: any) => void): void {
        if (this.socket) {
            this.socket.on('road-quality-update', callback);
        }
    }

    static disconnect(): void {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }
}
