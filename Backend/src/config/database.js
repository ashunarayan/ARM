const mongoose = require('mongoose');

/**
 * Connect to MongoDB
 */
const connectDB = async () => {
    try {
        if (!process.env.MONGODB_URI) {
            throw new Error('MONGODB_URI environment variable is not set');
        }

        const options = {
            // Connection pool size
            maxPoolSize: 10,
            minPoolSize: 2,

            // Server selection timeout
            serverSelectionTimeoutMS: 5000,

            // Socket timeout
            socketTimeoutMS: 45000,
        };

        const conn = await mongoose.connect(process.env.MONGODB_URI, options);

        console.log(`MongoDB Connected: ${conn.connection.host}`);

        // Handle connection events
        mongoose.connection.on('error', (err) => {
            console.error('MongoDB connection error:', err);
        });

        mongoose.connection.on('disconnected', () => {
            console.warn('MongoDB disconnected');
        });

        mongoose.connection.on('reconnected', () => {
            console.log('MongoDB reconnected');
        });

        // Graceful shutdown
        process.on('SIGINT', async () => {
            await mongoose.connection.close();
            console.log('MongoDB connection closed through app termination');
            process.exit(0);
        });

    } catch (error) {
        console.error('MongoDB connection failed:', error.message);
        process.exit(1);
    }
};

module.exports = connectDB;
