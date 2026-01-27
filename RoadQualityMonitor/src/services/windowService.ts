const WINDOW_SIZE = 20;

export interface SensorReading {
    ax: number; ay: number; az: number;
    wx: number; wy: number; wz: number;
    speed: number;
    timestamp: number;
    location: { latitude: number; longitude: number };
}

class WindowManager {
    private buffer: SensorReading[] = [];
    private onWindowReadyCallback: ((window: SensorReading[]) => void) | null = null;

    initialize(onWindowReady: (window: SensorReading[]) => void) {
        this.onWindowReadyCallback = onWindowReady;
        this.buffer = [];
    }

    addReading(reading: SensorReading) {
        this.buffer.push(reading);

        if (this.buffer.length >= WINDOW_SIZE) {
            const window = [...this.buffer];
            this.buffer = []; // Clear for next non-overlapping window
            
            if (this.onWindowReadyCallback) {
                this.onWindowReadyCallback(window);
            }
        }
    }
}

export const windowManager = new WindowManager();
