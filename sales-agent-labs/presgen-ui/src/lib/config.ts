/**
 * Centralized Configuration for PresGen UI
 *
 * All service URLs and ports are managed through environment variables
 * defined in the root .env file. This ensures consistency across all services
 * and makes port configuration changes easier to manage.
 *
 * Environment Variables:
 * - NEXT_PUBLIC_PRESGEN_ASSESS_URL: URL for PresGen-Assess service (default: http://localhost:8000)
 * - NEXT_PUBLIC_PRESGEN_CORE_URL: URL for PresGen-Core service (default: http://localhost:8080)
 */

// PresGen-Assess Service URL (port 8000)
export const PRESGEN_ASSESS_URL =
  process.env.NEXT_PUBLIC_PRESGEN_ASSESS_URL || 'http://localhost:8000';

// PresGen-Core Service URL (port 8080)
export const PRESGEN_CORE_URL =
  process.env.NEXT_PUBLIC_PRESGEN_CORE_URL || 'http://localhost:8080';

// Derived API endpoints
export const PRESGEN_ASSESS_API_URL = `${PRESGEN_ASSESS_URL}/api/v1`;
export const PRESGEN_CORE_API_URL = `${PRESGEN_CORE_URL}`;

// Legacy compatibility (for route handlers)
export const ASSESS_API_URL = PRESGEN_ASSESS_URL;

/**
 * Log configuration on initialization (development mode only)
 */
if (process.env.NODE_ENV === 'development') {
  console.log('🔧 PresGen UI Configuration:');
  console.log(`  📡 PresGen-Assess URL: ${PRESGEN_ASSESS_URL}`);
  console.log(`  📡 PresGen-Core URL: ${PRESGEN_CORE_URL}`);
  console.log(`  📡 PresGen-Assess API: ${PRESGEN_ASSESS_API_URL}`);
  console.log(`  📡 PresGen-Core API: ${PRESGEN_CORE_API_URL}`);
}
