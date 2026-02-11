export interface SecurityHeaders {
  contentTypeOptions: string;
  frameOptions: string;
  xssProtection: string;
  referrerPolicy: string;
}

export interface OperationalSettings {
  // Security settings
  maxRequestSize: number;
  requestTimeout: number;
  maxJsonDepth: number;
  maxStringLength: number;
  maxArrayItems: number;
  maxItemsPerArray: number;
  
  // Rate limiting
  rateLimitEnabled: boolean;
  rateLimitRequestsPerMinute: number;
  rateLimitBurstSize: number;
  apiKeyWindow: number;
  apiKeyMaxRequests: number;
  ipWindow: number;
  ipMaxRequests: number;
  
  // Audit settings
  auditLogEnabled: boolean;
  auditRetentionDays: number;
  auditExportBatchSize: number;
  auditLogRetentionDays: number;
  auditLogMaxFileSize: number;
  
  // CORS settings
  corsEnabled: boolean;
  corsAllowedOrigins: string[];
  corsOrigins: string[];
  corsAllowedMethods: string[];
  corsAllowedHeaders: string[];
  
  // Master password cache settings
  masterPasswordCacheEnabled: boolean;
  masterPasswordCacheTtlMinutes: number;
  masterPasswordTtlHours: number;
  masterPasswordIdleTimeoutMinutes: number;
  masterPasswordPerUserSession: boolean;
  
  // Security settings
  trustedProxies: string;
  securityHeaders: SecurityHeaders;
}

/**
 * Mock operational settings for development/demo purposes
 */
export const mockOperationalSettings: OperationalSettings = {
  // Security settings
  maxRequestSize: 10485760, // 10MB
  requestTimeout: 30,
  maxJsonDepth: 20,
  maxStringLength: 10000,
  maxArrayItems: 1000,
  maxItemsPerArray: 1000,
  
  // Rate limiting
  rateLimitEnabled: true,
  rateLimitRequestsPerMinute: 60,
  rateLimitBurstSize: 10,
  apiKeyWindow: 300,
  apiKeyMaxRequests: 1000,
  ipWindow: 60,
  ipMaxRequests: 100,
  
  // Audit settings
  auditLogEnabled: true,
  auditRetentionDays: 90,
  auditExportBatchSize: 1000,
  auditLogRetentionDays: 90,
  auditLogMaxFileSize: 104857600, // 100MB
  
  // CORS settings
  corsEnabled: true,
  corsAllowedOrigins: ['http://localhost:3000', 'https://wireguard-mesh-manager.example.com'],
  corsOrigins: ['http://localhost:3000', 'https://wireguard-mesh-manager.example.com'],
  corsAllowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  corsAllowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'X-API-Key',
    'X-CSRF-Token',
  ],
  
  // Master password cache settings
  masterPasswordCacheEnabled: true,
  masterPasswordCacheTtlMinutes: 60,
  masterPasswordTtlHours: 1,
  masterPasswordIdleTimeoutMinutes: 30,
  masterPasswordPerUserSession: true,
  
  // Security settings
  trustedProxies: '127.0.0.1, ::1',
  securityHeaders: {
    contentTypeOptions: 'nosniff',
    frameOptions: 'DENY',
    xssProtection: '1; mode=block',
    referrerPolicy: 'strict-origin-when-cross-origin',
  },
};
