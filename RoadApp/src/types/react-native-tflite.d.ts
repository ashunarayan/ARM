declare module 'react-native-tflite' {
    export interface ModelConfig {
        model: string;
        numThreads?: number;
    }

    export interface TFLiteModel {
        run(input: any): Promise<any>;
    }

    export class TFLite {
        static loadModel(config: ModelConfig): Promise<TFLiteModel>;
        static run(input: any, model: TFLiteModel): Promise<any>;
    }
}
