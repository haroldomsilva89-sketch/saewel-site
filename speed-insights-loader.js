/**
 * Vercel Speed Insights Loader
 * 
 * This script loads and initializes Vercel Speed Insights for performance monitoring.
 * Speed Insights tracks Core Web Vitals and other performance metrics.
 * 
 * Note: Speed Insights only collects data in production deployments on Vercel.
 * No data is collected in development mode.
 */

// Import the injectSpeedInsights function from the installed package
import { injectSpeedInsights } from './node_modules/@vercel/speed-insights/dist/index.mjs';

// Initialize Speed Insights with default configuration
// This will automatically detect if running on Vercel and start tracking metrics
injectSpeedInsights();
