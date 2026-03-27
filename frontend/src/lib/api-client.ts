/**
 * Comprehensive TypeScript API client for WireGuard Mesh Manager
 * Generated based on backend API structure and schemas
 */

import { z } from 'zod';
import { ensureCsrfToken, getCsrfToken, getMasterSessionToken } from './auth';

// Base schemas
export const PaginationSchema = z.object({
  page: z.number(),
  page_size: z.number(),
  total_count: z.number(),
  total_pages: z.number(),
  has_next: z.boolean(),
  has_previous: z.boolean(),
});

export type Pagination = z.infer<typeof PaginationSchema>;

// Network schemas
export const WireGuardNetworkBaseSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().optional().nullable(),
  network_cidr: z.string().regex(/^\d+\.\d+\.\d+\.\d+\/\d+$/),
  dns_servers: z.string().optional().nullable(),
  mtu: z.number().int().gt(0).max(9000).optional().nullable(),
  persistent_keepalive: z
    .number()
    .int()
    .min(0)
    .max(86400)
    .optional()
    .nullable(),
  interface_properties: z.record(z.string(), z.any()).optional().nullable(),
});

export const WireGuardNetworkCreateSchema = WireGuardNetworkBaseSchema.extend({
  preshared_key: z.string().min(44).max(44).optional().nullable(),
});
export const WireGuardNetworkUpdateSchema = WireGuardNetworkBaseSchema.extend({
  preshared_key: z.string().min(44).max(44).optional().nullable(),
}).partial();

export const WireGuardNetworkResponseSchema = WireGuardNetworkBaseSchema.extend({
  id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  location_count: z.number().default(0),
  device_count: z.number().default(0),
});

export const WireGuardNetworkListItemSchema = z.object({
  id: z.string(),
  name: z.string().min(1).max(100),
  description: z.string().optional().nullable(),
  network_cidr: z.string(),
  dns_servers: z.string().optional().nullable(),
  mtu: z.coerce.number().int().optional().nullable(),
  persistent_keepalive: z.coerce.number().int().optional().nullable(),
  interface_properties: z.record(z.string(), z.any()).optional().nullable(),
  created_at: z.string().optional().nullable(),
  updated_at: z.string().optional().nullable(),
  location_count: z.coerce.number().default(0),
  device_count: z.coerce.number().default(0),
});

export type WireGuardNetworkCreate = z.infer<
  typeof WireGuardNetworkCreateSchema
>;
export type WireGuardNetworkUpdate = z.infer<
  typeof WireGuardNetworkUpdateSchema
>;
export type WireGuardNetworkResponse = z.infer<
  typeof WireGuardNetworkResponseSchema
>;
export type WireGuardNetworkListItem = z.infer<
  typeof WireGuardNetworkListItemSchema
>;

// Location schemas
export const LocationBaseSchema = z.object({
  network_id: z.string(),
  name: z.string().min(1).max(100),
  description: z.string().optional().nullable(),
  external_endpoint: z.string().optional().nullable(),
  internal_endpoint: z.string().optional().nullable(),
  interface_properties: z.record(z.string(), z.any()).optional().nullable(),
});

export const LocationCreateSchema = LocationBaseSchema.extend({
  preshared_key: z.string().min(44).max(44).optional().nullable(),
});
export const LocationUpdateSchema = LocationBaseSchema.extend({
  preshared_key: z.string().min(44).max(44).optional().nullable(),
}).partial();

export const LocationResponseSchema = LocationBaseSchema.extend({
  id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  network_name: z.string().optional(),
  device_count: z.number().default(0),
});

export type LocationCreate = z.infer<typeof LocationCreateSchema>;
export type LocationUpdate = z.infer<typeof LocationUpdateSchema>;
export type LocationResponse = z.infer<typeof LocationResponseSchema>;

// Device schemas
export const DeviceBaseSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(1000).optional().nullable(),
  enabled: z.boolean().default(true),
  interface_properties: z.record(z.string(), z.any()).optional().nullable(),
  wireguard_ip: z.string().regex(/^\d+\.\d+\.\d+\.\d+$/).optional().nullable(),
  external_endpoint_host: z.string().optional().nullable(),
  external_endpoint_port: z.number().int().min(1).max(65535).optional().nullable(),
  internal_endpoint_host: z.string().optional().nullable(),
  internal_endpoint_port: z.number().int().min(1).max(65535).optional().nullable(),
});

export const DeviceCreateSchema = DeviceBaseSchema.extend({
  network_id: z.string(),
  location_id: z.string(),
  public_key: z.string().min(44).max(56),
  private_key: z.string().min(44).max(56),
  preshared_key: z.string().min(44).max(56).optional().nullable(),
});

export const DeviceUpdateSchema = DeviceBaseSchema.extend({
  public_key: z.string().min(44).max(56).optional().nullable(),
  private_key: z.string().min(44).max(56).optional().nullable(),
  preshared_key: z.string().min(44).max(56).optional().nullable(),
  location_id: z.string().optional().nullable(),
}).partial();

export const DeviceResponseSchema = DeviceBaseSchema.extend({
  id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  network_id: z.string(),
  location_id: z.string(),
  network_name: z.string().optional().nullable(),
  location_name: z.string().optional().nullable(),
  location_external_endpoint: z.string().optional().nullable(),
  public_key: z.string(),
  preshared_key_encrypted: z.string().optional().nullable(),
  private_key_encrypted: z.string().optional().nullable(),
  api_key: z.string().optional().nullable(),
  api_key_last_used: z.string().optional().nullable(),
  endpoint_allowlist: z.array(z.string()).default([]),
});

export const DevicePeerLinkPropertiesSchema = z.record(
  z.string(),
  z.union([z.string(), z.number(), z.boolean()]).optional().nullable()
);

export const DevicePeerLinkSchema = z.object({
  id: z.string(),
  network_id: z.string(),
  from_device_id: z.string(),
  to_device_id: z.string(),
  properties: DevicePeerLinkPropertiesSchema.optional().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const DevicePeerLinkCreateSchema = z.object({
  from_device_id: z.string(),
  to_device_id: z.string(),
  properties: DevicePeerLinkPropertiesSchema.optional().nullable(),
  preshared_key: z.string().optional().nullable(),
});

export type DevicePeerLink = z.infer<typeof DevicePeerLinkSchema>;
export type DevicePeerLinkCreate = z.infer<typeof DevicePeerLinkCreateSchema>;

export const DeviceAllocationResponseSchema = z.object({
  device: DeviceResponseSchema,
  allocated_ip: z.string().optional(),
  allocation_status: z.enum(['allocated', 'provided', 'error']),
});

// API key schemas (minimal fields needed for regeneration flows)
export const ApiKeyCreateResponseSchema = z
  .object({
    key_value: z.string(),
  })
  .passthrough();

// Key generation schemas
export const KeyGenerationMethodSchema = z.object({
  method: z.enum(['cli', 'crypto']),
});

export const WireGuardKeyPairResponseSchema = z.object({
  private_key: z.string(),
  public_key: z.string(),
  method: z.enum(['cli', 'crypto']),
});

export const WireGuardPresharedKeyResponseSchema = z.object({
  preshared_key: z.string().min(44).max(44),
});

export const DeviceKeysRegenerateResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  public_key: z.string(),
  private_key_encrypted: z.boolean(),
});

export type KeyGenerationMethod = z.infer<typeof KeyGenerationMethodSchema>;
export type WireGuardKeyPairResponse = z.infer<typeof WireGuardKeyPairResponseSchema>;
export type WireGuardPresharedKeyResponse = z.infer<
  typeof WireGuardPresharedKeyResponseSchema
>;
export type DeviceKeysRegenerateResponse = z.infer<typeof DeviceKeysRegenerateResponseSchema>;

export type DeviceCreate = z.infer<typeof DeviceCreateSchema>;
export type DeviceUpdate = z.infer<typeof DeviceUpdateSchema>;
export type DeviceResponse = z.infer<typeof DeviceResponseSchema>;
export type DeviceAllocationResponse = z.infer<
  typeof DeviceAllocationResponseSchema
>;

// Device Config schemas
export const DeviceConfigResponseSchema = z.object({
  device_id: z.string(),
  device_name: z.string(),
  network_name: z.string(),
  configuration: z.union([z.string(), z.record(z.string(), z.any())]),
  format: z.string(),
  created_at: z.string(),
});

export type DeviceConfigResponse = z.infer<typeof DeviceConfigResponseSchema>;

// Audit event schemas
export const AuditEventSchema = z.object({
  id: z.string(),
  network_id: z.string(),
  network_name: z.string().optional().nullable(),
  actor: z.string(),
  action: z.string(),
  resource_type: z.string(),
  resource_id: z.string().optional().nullable(),
  created_at: z.string(),
  details: z.any().optional().nullable(),
});

export const AuditEventListSchema = z.object({
  events: z.array(AuditEventSchema),
  pagination: PaginationSchema,
  filters_applied: z.object({
    network_id: z.string().optional().nullable(),
    start_date: z.string().optional().nullable(),
    end_date: z.string().optional().nullable(),
    actor: z.string().optional().nullable(),
    action: z.string().optional().nullable(),
    resource_type: z.string().optional().nullable(),
  }),
});

export type AuditEvent = z.infer<typeof AuditEventSchema>;
export type AuditEventList = z.infer<typeof AuditEventListSchema>;

// Health check schemas
export const HealthCheckResponseSchema = z.object({
  status: z.enum(['healthy', 'unhealthy', 'degraded']),
  timestamp: z.string(),
  version: z.string(),
  uptime_seconds: z.number(),
  database_status: z.enum(['healthy', 'unhealthy']),
  memory_usage_mb: z.number().optional(),
});

export const MetricsResponseSchema = z.object({
  request_count: z.number(),
  error_count: z.number(),
  avg_response_time_ms: z.number(),
  active_connections: z.number().optional(),
});

export type HealthCheckResponse = z.infer<typeof HealthCheckResponseSchema>;
export type MetricsResponse = z.infer<typeof MetricsResponseSchema>;

// Key rotation schemas
export const MasterPasswordRotateSchema = z
  .object({
    current_password: z.string().min(1),
    new_password: z.string().min(1),
    confirm_password: z.string().min(1),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Passwords must match',
    path: ['confirm_password'],
  });

export const KeyRotationStatusSchema = z.object({
  total_networks: z.number(),
  total_devices: z.number(),
  rotated_networks: z.number(),
  rotated_devices: z.number(),
  failed_networks: z.number(),
  failed_devices: z.number(),
  errors: z.array(z.string()),
  session_invalidated: z.boolean().default(false),
});

export const KeyRotationEstimateSchema = z.object({
  total_networks: z.number(),
  total_devices: z.number(),
  total_keys: z.number(),
});

export const PasswordValidationSchema = z.object({
  valid: z.boolean(),
});

export const PasswordStrengthValidationSchema = z.object({
  is_valid: z.boolean(),
  strength: z.number(),
  score: z.number(),
  feedback: z.array(z.string()),
});

export const PasswordPolicySchema = z.object({
  requirements: z.array(z.string()),
  min_length: z.number(),
  max_length: z.number(),
});

export type MasterPasswordRotate = z.infer<typeof MasterPasswordRotateSchema>;
export type KeyRotationStatus = z.infer<typeof KeyRotationStatusSchema>;
export type KeyRotationEstimate = z.infer<typeof KeyRotationEstimateSchema>;
export type PasswordValidation = z.infer<typeof PasswordValidationSchema>;
export type PasswordStrengthValidation = z.infer<
  typeof PasswordStrengthValidationSchema
>;

// Master Password schemas
export const MasterPasswordUnlockRequestSchema = z.object({
  master_password: z.string(),
  ttl_hours: z.number().optional().nullable(),
});

export const MasterPasswordUnlockResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  expires_at: z.string().optional().nullable(),
  password_id: z.string().optional().nullable(),
  session_token: z.string().optional().nullable(),
});

export const MasterPasswordStatusResponseSchema = z.object({
  is_unlocked: z.boolean(),
  password_id: z.string().optional().nullable(),
  expires_at: z.string().optional().nullable(),
  idle_expires_at: z.string().optional().nullable(),
  access_count: z.number(),
  last_access: z.string().optional().nullable(),
  ttl_seconds: z.number(),
  idle_ttl_seconds: z.number(),
  session_id: z.string().optional().nullable(),
});

export const MasterPasswordExtendTTLRequestSchema = z.object({
  additional_hours: z.number().min(0.1).max(24.0).default(1.0),
});

export const MasterPasswordExtendTTLResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  new_expires_at: z.string().optional().nullable(),
});

export const MasterPasswordIsUnlockedResponseSchema = z.object({
  is_unlocked: z.boolean(),
});

export type MasterPasswordUnlockRequest = z.infer<
  typeof MasterPasswordUnlockRequestSchema
>;
export type MasterPasswordUnlockResponse = z.infer<
  typeof MasterPasswordUnlockResponseSchema
>;
export type MasterPasswordStatusResponse = z.infer<
  typeof MasterPasswordStatusResponseSchema
>;
export type MasterPasswordExtendTTLRequest = z.infer<
  typeof MasterPasswordExtendTTLRequestSchema
>;
export type MasterPasswordExtendTTLResponse = z.infer<
  typeof MasterPasswordExtendTTLResponseSchema
>;
export type MasterPasswordIsUnlockedResponse = z.infer<
  typeof MasterPasswordIsUnlockedResponseSchema
>;
export type PasswordPolicy = z.infer<typeof PasswordPolicySchema>;

// Config lint schemas
export const SeveritySchema = z.enum(['error', 'warning', 'info']);
export const CategorySchema = z.enum([
  'network',
  'location',
  'device',
  'general',
]);

export const LocationLintSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().optional().nullable(),
  external_endpoint: z.string().optional().nullable(),
});

export const DeviceLintSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().optional().nullable(),
  wireguard_ip: z.string().optional().nullable(),
  public_key: z.string().optional().nullable(),
  preshared_key: z.string().optional().nullable(),
  enabled: z.boolean().default(true),
});

export const LintIssueSchema = z.object({
  severity: SeveritySchema,
  category: CategorySchema,
  field: z.string(),
  message: z.string(),
  suggestion: z.string().optional(),
});

export const ConfigLintRequestSchema = z.object({
  network_cidr: z.string(),
  dns_servers: z.string().optional(),
  mtu: z.number().int().gt(0).max(9000).optional(),
  persistent_keepalive: z.number().int().min(0).max(86400).optional(),
  public_key: z.string().optional(),
  locations: z.array(LocationLintSchema).default([]),
  devices: z.array(DeviceLintSchema).default([]),
});

export const ConfigLintResponseSchema = z.object({
  valid: z.boolean(),
  issue_count: z.record(z.string(), z.number()).default({}),
  issues: z.array(LintIssueSchema).default([]),
  summary: z.string(),
});

export type Severity = z.infer<typeof SeveritySchema>;
export type Category = z.infer<typeof CategorySchema>;
export type LocationLint = z.infer<typeof LocationLintSchema>;
export type DeviceLint = z.infer<typeof DeviceLintSchema>;
export type LintIssue = z.infer<typeof LintIssueSchema>;
export type ConfigLintRequest = z.infer<typeof ConfigLintRequestSchema>;
export type ConfigLintResponse = z.infer<typeof ConfigLintResponseSchema>;

// Export schemas
export const ExportRequestSchema = z.object({
  network_ids: z.array(z.string()).optional(),
  include_configs: z.boolean().default(true),
  include_api_keys: z.boolean().default(false),
  format: z.enum(['json', 'zip']).default('json'),
});

export const NetworkExportSchema = z.object({
  name: z.string(),
  description: z.string().optional().nullable(),
  network_cidr: z.string(),
  dns_servers: z.string().optional().nullable(),
  mtu: z.number().optional().nullable(),
  persistent_keepalive: z.number().optional().nullable(),
  locations: z.array(z.any()).optional().nullable(),
  devices: z.array(z.any()).optional().nullable(),
});

export const ExportDataSchema = z.object({
  metadata: z.object({
    version: z.string(),
    exported_at: z.string(),
    exported_by: z.string(),
    description: z.string().optional(),
  }),
  networks: z.array(NetworkExportSchema),
});

export type ExportRequest = z.infer<typeof ExportRequestSchema>;
export type ExportData = z.infer<typeof ExportDataSchema>;

// Operational settings schemas
export const OperationalSettingsResponseSchema = z.object({
  // Request hardening settings
  max_request_size: z.number(),
  request_timeout: z.number(),
  max_json_depth: z.number(),
  max_string_length: z.number(),
  max_items_per_array: z.number(),
  // Rate limiting settings
  rate_limit_api_key_window: z.number(),
  rate_limit_api_key_max_requests: z.number(),
  rate_limit_ip_window: z.number(),
  rate_limit_ip_max_requests: z.number(),
  // Audit settings
  audit_retention_days: z.number(),
  audit_export_batch_size: z.number(),
  // Master password cache settings
  master_password_ttl_hours: z.number(),
  master_password_idle_timeout_minutes: z.number(),
  master_password_per_user_session: z.boolean(),
  // Trusted proxy settings
  trusted_proxies: z.string(),
  // CORS settings
  cors_origins: z.string(),
  cors_allow_credentials: z.boolean(),
  // Logo settings
  logo_bg_color: z.string(),
  logo_text: z.string(),
  app_name: z.string(),
});

export const OperationalSettingsUpdateSchema = z.object({
  // Request hardening settings
  max_request_size: z.number().optional(),
  request_timeout: z.number().optional(),
  max_json_depth: z.number().optional(),
  max_string_length: z.number().optional(),
  max_items_per_array: z.number().optional(),
  // Rate limiting settings
  rate_limit_api_key_window: z.number().optional(),
  rate_limit_api_key_max_requests: z.number().optional(),
  rate_limit_ip_window: z.number().optional(),
  rate_limit_ip_max_requests: z.number().optional(),
  // Audit settings
  audit_retention_days: z.number().optional(),
  audit_export_batch_size: z.number().optional(),
  // Master password cache settings
  master_password_ttl_hours: z.number().optional(),
  master_password_idle_timeout_minutes: z.number().optional(),
  master_password_per_user_session: z.boolean().optional(),
  // Trusted proxy settings
  trusted_proxies: z.string().optional(),
  // CORS settings
  cors_origins: z.string().optional(),
  cors_allow_credentials: z.boolean().optional(),
  // Logo settings
  logo_bg_color: z.string().optional(),
  logo_text: z.string().optional(),
  app_name: z.string().optional(),
});

export type OperationalSettingsResponse = z.infer<typeof OperationalSettingsResponseSchema>;
export type OperationalSettingsUpdate = z.infer<typeof OperationalSettingsUpdateSchema>;

// Error schemas
export const ErrorResponseSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.any().optional(),
  }),
});

export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

// API Client parameters
export interface AuditEventParams {
  network_id?: string;
  start_date?: string;
  end_date?: string;
  actor?: string;
  action?: string;
  resource_type?: string;
  page?: number;
  page_size?: number;
  include_details?: boolean;
}

export interface AuditExportParams extends Omit<
  AuditEventParams,
  'page' | 'page_size'
> {
  format?: 'json' | 'csv';
}

export interface AuditStatistics {
  total_events: number;
  recent_events_24h: number;
  recent_events_7d: number;
  expired_events: number;
  actions_breakdown: Array<{
    action: string;
    count: number;
  }>;
  recent_actions_breakdown_24h: Array<{
    action: string;
    count: number;
  }>;
  recent_actions_breakdown_7d: Array<{
    action: string;
    count: number;
  }>;
  retention_days: number;
  storage_stats: {
    total_size_bytes: number;
    database_size_bytes: number;
    wal_size_bytes: number;
    shm_size_bytes: number;
    backup_size_bytes: number;
    breakdown: Array<{
      file: string;
      path: string;
      size_bytes: number;
      type: string;
    }>;
    events_per_day: number;
  };
}

export interface NetworkListParams {
  page?: number;
  page_size?: number;
  search?: string;
}

export interface DeviceListParams {
  network_id?: string;
  location_id?: string;
  enabled?: boolean;
  page?: number;
  page_size?: number;
  search?: string;
}

export interface LocationListParams {
  network_id?: string;
  page?: number;
  page_size?: number;
  search?: string;
}

type ApiErrorDetails = {
  detail?: string;
  error?: string;
  message?: string;
  details?: Array<{
    loc?: Array<string | number>;
    msg?: string;
  }>;
};

type FieldErrorMap = Record<string, string>;

const formatValidationDetails = (details: ApiErrorDetails['details']): string | null => {
  if (!details || details.length === 0) {
    return null;
  }

  const formatted = details.slice(0, 3).map((entry) => {
    const location =
      entry.loc && entry.loc.length > 0
        ? entry.loc
            .filter((part) => part !== 'body')
            .map((part) => part.toString())
            .join('.')
        : 'request';
    const message = entry.msg || 'Invalid value';
    return `${location}: ${message}`;
  });

  const suffix = details.length > 3 ? ` (+${details.length - 3} more)` : '';
  return `${formatted.join('; ')}${suffix}`;
};

const SENSITIVE_KEYS = new Set([
  'api_key',
  'authorization',
  'device_dek',
  'key',
  'key_value',
  'master_password',
  'preshared_key',
  'private_key',
  'public_key',
]);

const redactSensitive = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map((entry) => redactSensitive(entry));
  }

  if (value && typeof value === 'object') {
    const sanitized: Record<string, unknown> = {};
    Object.entries(value as Record<string, unknown>).forEach(([key, val]) => {
      if (SENSITIVE_KEYS.has(key.toLowerCase())) {
        sanitized[key] = '[redacted]';
      } else {
        sanitized[key] = redactSensitive(val);
      }
    });
    return sanitized;
  }

  return value;
};

const redactBodyForLog = (body: BodyInit | null | undefined): unknown => {
  if (!body) {
    return null;
  }

  if (typeof body === 'string') {
    try {
      const parsed = JSON.parse(body);
      return redactSensitive(parsed);
    } catch {
      return '[redacted]';
    }
  }

  if (body instanceof FormData) {
    return '[form-data]';
  }

  return '[redacted]';
};

const redactErrorText = (text: string): string => {
  try {
    const parsed = JSON.parse(text);
    return JSON.stringify(redactSensitive(parsed));
  } catch {
    return text;
  }
};

const buildApiErrorMessage = (
  errorData: ApiErrorDetails | null,
  fallbackText: string
): string => {
  if (!errorData) {
    return fallbackText;
  }

  if (errorData.detail) {
    return errorData.detail;
  }

  if (errorData.message) {
    const validationDetails = formatValidationDetails(errorData.details);
    return validationDetails
      ? `${errorData.message}: ${validationDetails}`
      : errorData.message;
  }

  if (errorData.error) {
    return errorData.error;
  }

  return fallbackText;
};

const extractFieldErrors = (
  details: ApiErrorDetails['details']
): FieldErrorMap => {
  if (!details) {
    return {};
  }

  const fieldErrors: FieldErrorMap = {};
  details.forEach((entry) => {
    if (!entry.loc || entry.loc.length === 0 || !entry.msg) {
      return;
    }

    const locationParts = entry.loc
      .filter((part) => part !== 'body')
      .map((part) => part.toString());
    const fieldKey = locationParts[0] || 'request';

    if (!fieldErrors[fieldKey]) {
      fieldErrors[fieldKey] = entry.msg;
    }
  });

  return fieldErrors;
};

// Main API Client class
export class WireGuardApiClient {
  private defaultHeaders: Record<string, string>;

  constructor(
    options: {
      headers?: Record<string, string>;
    } = {}
  ) {
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
  }

  private getApiPath(
    endpoint: string,
    prefix: 'api' | 'master-password' | 'key-rotation' | 'api-keys' | 'csrf'
  ): string {
    const basePath = prefix === 'api' ? '/api' : `/api/${prefix}`;
    return `${basePath}${endpoint}`;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    prefix:
      | 'api'
      | 'master-password'
      | 'key-rotation'
      | 'api-keys'
      | 'csrf' = 'api',
    retryOnCsrf = true,
    retryOnNetwork = true,
    responseType: 'json' | 'text' | 'blob' = 'json',
    retryCount = 0,
    maxRetries = 3
  ): Promise<T> {
    const url = this.getApiPath(endpoint, prefix);

    const method = (options.method || 'GET').toUpperCase();
    const isIdempotent = ['GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE'].includes(
      method
    );
    const headers: Record<string, string> = {
      ...this.defaultHeaders,
      ...(options.headers as Record<string, string> | undefined),
    };

    const sessionToken = getMasterSessionToken();
    if (sessionToken && !headers.Authorization) {
      headers.Authorization = `Master ${sessionToken}`;
    }

    if (method !== 'GET' && method !== 'HEAD') {
      await ensureCsrfToken();
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
    }

    const config: RequestInit = {
      headers,
      credentials: 'same-origin',
      ...options,
    };

    let response: Response;
    try {
      response = await fetch(url, config);
    } catch (error) {
      if (
        retryOnNetwork &&
        isIdempotent &&
        retryCount < maxRetries &&
        error instanceof Error &&
        (error.message.toLowerCase().includes('failed to fetch') ||
          error.message.toLowerCase().includes('network'))
      ) {
        const delay = Math.pow(2, retryCount) * 1000;
        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.request(
          endpoint,
          options,
          prefix,
          retryOnCsrf,
          false,
          responseType,
          retryCount + 1,
          maxRetries
        );
      }
      throw error;
    }

    if (!response.ok) {
      const errorText = await response.text();
      const isUnauthorized = response.status === 401;
      const isLocked = response.status === 423;
      const isUnprocessableEntity = response.status === 422;
      const isRateLimit = response.status === 429;
      const isServerError = response.status >= 500 && response.status < 600;
      const isCsrfFailure =
        response.status === 403 &&
        method !== 'GET' &&
        method !== 'HEAD' &&
        errorText.toLowerCase().includes('csrf token');

      // Log 422 errors for debugging
      if (isUnprocessableEntity) {
        console.error('422 Unprocessable Entity - Request Details:', {
          endpoint,
          method,
          status: response.status,
          errorText: redactErrorText(errorText),
          requestBody: redactBodyForLog(options.body),
        });
        try {
          const errorData = JSON.parse(errorText);
          console.error('422 Error Details:', redactSensitive(errorData));
        } catch {
          console.error('Could not parse error response as JSON');
        }
      }

      // Handle 429 Rate Limit errors with Retry-After
      if (isRateLimit && isIdempotent && retryCount < maxRetries) {
        const retryAfter = response.headers.get('Retry-After');
        const delay = retryAfter ? parseInt(retryAfter, 10) * 1000 : 60000;
        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.request(
          endpoint,
          options,
          prefix,
          retryOnCsrf,
          retryOnNetwork,
          responseType,
          retryCount + 1,
          maxRetries
        );
      }

      // Handle 5xx Server errors with exponential backoff retry
      if (isServerError && isIdempotent && retryCount < maxRetries) {
        const delay = Math.pow(2, retryCount) * 1000;
        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.request(
          endpoint,
          options,
          prefix,
          retryOnCsrf,
          retryOnNetwork,
          responseType,
          retryCount + 1,
          maxRetries
        );
      }

      if (isCsrfFailure && retryOnCsrf) {
        await ensureCsrfToken(true);
        return this.request(
          endpoint,
          options,
          prefix,
          false,
          retryOnNetwork,
          responseType,
          retryCount + 1,
          maxRetries
        );
      }

      const error = new Error(
        `API request failed: ${response.status}`
      ) as Error & { status?: number; isUnauthorized?: boolean; isLocked?: boolean; data?: ApiErrorDetails; fieldErrors?: FieldErrorMap; retryAfter?: number };

      error.status = response.status;

      if (isUnauthorized) {
        error.isUnauthorized = true;
      }

      if (isLocked) {
        error.isLocked = true;
      }

      if (isUnauthorized) {
        error.isUnauthorized = true;
      }

      if (isLocked) {
        error.isLocked = true;
      }

      if (isRateLimit) {
        const retryAfterHeader = response.headers.get('Retry-After');
        if (retryAfterHeader) {
          error.retryAfter = parseInt(retryAfterHeader, 10);
        }
      }

      try {
        const errorData = JSON.parse(errorText) as ApiErrorDetails;
        const message = buildApiErrorMessage(errorData, errorText);
        error.message = `API request failed: ${response.status} - ${message}`;
        error.data = errorData;
        error.fieldErrors = extractFieldErrors(errorData.details);
      } catch {
        error.message = `API request failed: ${response.status} - ${errorText}`;
      }

      throw error;
    }

    // Handle response based on responseType parameter
    if (responseType === 'blob') {
      return response.blob() as unknown as T;
    }

    if (responseType === 'text') {
      return response.text() as unknown as T;
    }

    // Handle empty responses for JSON
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }

    return response.text() as unknown as T;
  }

  // Health and metrics
  async getHealth(): Promise<HealthCheckResponse> {
    return this.request('/health');
  }

  async getMetrics(): Promise<MetricsResponse> {
    return this.request('/metrics');
  }

  // Networks
  async listNetworks(
    params?: NetworkListParams
  ): Promise<WireGuardNetworkListItem[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, value.toString());
        }
      });
    }

    const endpoint = `/networks${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const data = await this.request(endpoint);
    const parsed = z.array(WireGuardNetworkListItemSchema).safeParse(data);
    if (!parsed.success) {
      const error = new Error(
        'Unexpected response format while loading networks.'
      ) as Error & { details?: unknown };
      error.details = parsed.error.format();
      throw error;
    }
    return parsed.data;
  }

  async getNetwork(id: string): Promise<WireGuardNetworkResponse> {
    return this.request(`/networks/${id}`);
  }

  async createNetwork(
    data: WireGuardNetworkCreate
  ): Promise<WireGuardNetworkResponse> {
    return this.request('/networks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateNetwork(
    id: string,
    data: WireGuardNetworkUpdate
  ): Promise<WireGuardNetworkResponse> {
    return this.request(`/networks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteNetwork(id: string): Promise<{ message: string }> {
    return this.request(`/networks/${id}`, {
      method: 'DELETE',
    });
  }

  // Locations
  async listLocations(
    params?: LocationListParams
  ): Promise<LocationResponse[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, value.toString());
        }
      });
    }

    const endpoint = `/locations${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const data = await this.request(endpoint);
    return z.array(LocationResponseSchema).parse(data);
  }

  async getLocation(id: string): Promise<LocationResponse> {
    return this.request(`/locations/${id}`);
  }

  async createLocation(data: LocationCreate): Promise<LocationResponse> {
    return this.request('/locations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateLocation(
    id: string,
    data: LocationUpdate
  ): Promise<LocationResponse> {
    return this.request(`/locations/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteLocation(id: string): Promise<{ message: string }> {
    return this.request(`/locations/${id}`, {
      method: 'DELETE',
    });
  }

  // Devices
  async listDevices(params?: DeviceListParams): Promise<DeviceResponse[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, value.toString());
        }
      });
    }

    const endpoint = `/devices${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const data = await this.request(endpoint);
    return z.array(DeviceResponseSchema).parse(data);
  }

  // Device peer links
  async listDevicePeerLinks(networkId: string): Promise<DevicePeerLink[]> {
    const data = await this.request(`/networks/${networkId}/device-links`);
    return z.array(DevicePeerLinkSchema).parse(data);
  }

  async upsertDevicePeerLink(
    networkId: string,
    payload: DevicePeerLinkCreate
  ): Promise<DevicePeerLink> {
    return this.request(`/networks/${networkId}/device-links`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async deleteDevicePeerLink(
    networkId: string,
    fromDeviceId: string,
    toDeviceId: string
  ): Promise<{ message: string }> {
    return this.request(
      `/networks/${networkId}/device-links/${fromDeviceId}/${toDeviceId}`,
      {
        method: 'DELETE',
      }
    );
  }

  async getDevice(id: string): Promise<DeviceResponse> {
    return this.request(`/devices/${id}`);
  }

  async createDevice(data: DeviceCreate): Promise<DeviceResponse> {
    const response = await this.request('/devices', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return DeviceResponseSchema.parse(response);
  }

  async updateDevice(id: string, data: DeviceUpdate): Promise<DeviceResponse> {
    return this.request(`/devices/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteDevice(id: string): Promise<{ message: string }> {
    return this.request(`/devices/${id}`, {
      method: 'DELETE',
    });
  }

  async regenerateDeviceApiKey(id: string): Promise<{ api_key: string }> {
    const response = await this.request(
      `/devices/${id}/regenerate-api-key`,
      {
        method: 'POST',
      }
    );
    const parsedResponse = ApiKeyCreateResponseSchema.parse(response);
    return { api_key: parsedResponse.key_value };
  }

  // Device Configuration
  async getDeviceConfig(
    id: string,
    params?: { format?: 'wg' }
  ): Promise<DeviceConfigResponse> {
    const searchParams = new URLSearchParams();
    if (params?.format) {
      searchParams.append('format', params.format);
    }

    const endpoint = `/devices/${id}/config${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.request(endpoint);
  }

  async getAdminDeviceConfig(
    id: string,
    params?: { format?: 'wg' | 'json' | 'mobile'; platform?: string }
  ): Promise<DeviceConfigResponse> {
    const searchParams = new URLSearchParams();
    if (params?.format) {
      searchParams.append('format', params.format);
    }
    if (params?.platform) {
      searchParams.append('platform', params.platform);
    }

    const endpoint = `/devices/admin/${id}/config${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.request(endpoint);
  }

  async downloadAdminDeviceConfig(id: string): Promise<void> {
    const endpoint = `/devices/admin/${id}/config/wg`;

    // Use standard request method with blob response type
    const blob = await this.request<Blob>(
      endpoint,
      {},
      'api',
      true,
      true,
      'blob'
    );

    // Get filename from response headers - need to access the original response
    // Since we don't have access to headers here, use a reasonable default
    let filename = 'device_config.conf';

    // Try to get device name from cache or use the ID
    // We'll need to fetch device info or use a sensible default
    // For now, use the device ID in the filename
    filename = `device_${id}_wg0.conf`;

    // Create blob and download
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(a);
  }

  async getDeviceConfigByApiKey(
    deviceId: string,
    apiKey: string,
    params?: { format?: 'wg' }
  ): Promise<DeviceConfigResponse> {
    const searchParams = new URLSearchParams();
    if (params?.format) {
      searchParams.append('format', params.format);
    }

    const endpoint = `/devices/${deviceId}/config${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return this.request(endpoint, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });
  }

  // Key Generation
  async generateWireGuardKeys(
    method: KeyGenerationMethod
  ): Promise<WireGuardKeyPairResponse> {
    const response = await this.request('/devices/generate-keys', {
      method: 'POST',
      body: JSON.stringify(method),
    });
    return WireGuardKeyPairResponseSchema.parse(response);
  }

  async generateWireGuardPresharedKey(): Promise<WireGuardPresharedKeyResponse> {
    const response = await this.request('/devices/generate-preshared-key', {
      method: 'POST',
    });
    return WireGuardPresharedKeyResponseSchema.parse(response);
  }

  async regenerateDeviceKeys(
    deviceId: string,
    method: KeyGenerationMethod
  ): Promise<DeviceKeysRegenerateResponse> {
    const response = await this.request(`/devices/${deviceId}/regenerate-keys`, {
      method: 'POST',
      body: JSON.stringify(method),
    });
    return DeviceKeysRegenerateResponseSchema.parse(response);
  }

  // Export
  async exportNetworks(data: ExportRequest): Promise<ExportData> {
    const response = await this.request('/export', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return ExportDataSchema.parse(response);
  }

  async downloadExport(data: ExportRequest): Promise<Blob> {
    return this.request<Blob>(
      '/export/download',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      'api',
      true,
      true,
      'blob'
    );
  }

  async downloadNetworkConfigs(
    networkId: string,
    options: {
      format?: 'wg' | 'json' | 'mobile';
      includePresharedKeys?: boolean;
    } = {}
  ): Promise<Blob> {
    const payload = {
      format: options.format ?? 'wg',
      include_preshared_keys: options.includePresharedKeys ?? false,
    };
    const endpoint = `/export/networks/${networkId}/configs`;
    return this.request<Blob>(
      endpoint,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      'api',
      true,
      true,
      'blob'
    );
  }

  // Audit
  async getAuditEvents(params?: AuditEventParams): Promise<AuditEventList> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, value.toString());
        }
      });
    }

    const endpoint = `/audit/events${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const response = await this.request(endpoint);
    return AuditEventListSchema.parse(response);
  }

  async getAuditStatistics(): Promise<AuditStatistics> {
    return this.request('/audit/statistics');
  }

  async exportAuditEvents(params: AuditExportParams = {}): Promise<string> {
    if (typeof window === 'undefined') {
      throw new Error('Export functionality is only available in the browser');
    }

    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, value.toString());
      }
    });

    const endpoint = `/audit/export/download${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const blob = await this.request<Blob>(
      endpoint,
      {},
      'api',
      true,
      true,
      'blob'
    );
    return URL.createObjectURL(blob);
  }

  async getRetentionInfo(): Promise<{
    retention_days: number;
    cutoff_date: string;
    expired_events_count: number;
    export_batch_size: number;
  }> {
    return this.request('/audit/retention/info');
  }

  async cleanupExpiredEvents(): Promise<{
    events_deleted: number;
    cutoff_date: string;
    retention_days: number;
  }> {
    return this.request('/audit/cleanup', {
      method: 'POST',
    });
  }

  // Key Rotation
  async getRotationEstimate(): Promise<KeyRotationEstimate> {
    const response = await this.request('/estimate', {}, 'key-rotation');
    return KeyRotationEstimateSchema.parse(response);
  }

  async validateCurrentPassword(
    currentPassword: string
  ): Promise<PasswordValidation> {
    const response = await this.request(
      '/validate-current-password',
      {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword }),
      },
      'key-rotation'
    );
    return PasswordValidationSchema.parse(response);
  }

  async validatePassword(
    password: string
  ): Promise<PasswordStrengthValidation> {
    const response = await this.request('/validate-password', {
      method: 'POST',
      body: JSON.stringify({ password: password }),
    }, 'key-rotation');
    return PasswordStrengthValidationSchema.parse(response);
  }

  async getPasswordPolicy(): Promise<PasswordPolicy> {
    const response = await this.request('/password-policy', {}, 'key-rotation');
    return PasswordPolicySchema.parse(response);
  }

  async rotateMasterPassword(
    data: MasterPasswordRotate
  ): Promise<KeyRotationStatus> {
    const response = await this.request('/rotate', {
      method: 'POST',
      body: JSON.stringify(data),
    }, 'key-rotation');
    return KeyRotationStatusSchema.parse(response);
  }

  // Master Password Management
  async unlockMasterPassword(
    data: MasterPasswordUnlockRequest
  ): Promise<MasterPasswordUnlockResponse> {
    const response = await this.request('/unlock', {
      method: 'POST',
      body: JSON.stringify(data),
    }, 'master-password');
    return MasterPasswordUnlockResponseSchema.parse(response);
  }

  async lockMasterPassword(): Promise<MasterPasswordUnlockResponse> {
    const response = await this.request('/lock', {
      method: 'POST',
    }, 'master-password');
    return MasterPasswordUnlockResponseSchema.parse(response);
  }

  async isMasterPasswordUnlocked(): Promise<MasterPasswordIsUnlockedResponse> {
    const response = await this.request('/is-unlocked', {}, 'master-password');
    return MasterPasswordIsUnlockedResponseSchema.parse(response);
  }

  async getMasterPasswordStatus(): Promise<MasterPasswordStatusResponse> {
    const response = await this.request('/status', {}, 'master-password');
    return MasterPasswordStatusResponseSchema.parse(response);
  }

  async extendMasterPasswordTTL(
    data: MasterPasswordExtendTTLRequest
  ): Promise<MasterPasswordExtendTTLResponse> {
    const response = await this.request('/extend-ttl', {
      method: 'POST',
      body: JSON.stringify(data),
    }, 'master-password');
    return MasterPasswordExtendTTLResponseSchema.parse(response);
  }

  async refreshMasterPasswordAccess(): Promise<{ message: string }> {
    return this.request('/refresh-access', {
      method: 'POST',
    }, 'master-password');
  }

  // Config lint
  async lintNetworkConfig(
    config: ConfigLintRequest
  ): Promise<ConfigLintResponse> {
    const response = await this.request('/config-lint', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    return ConfigLintResponseSchema.parse(response);
  }

  // Operational settings
  async getOperationalSettings(): Promise<OperationalSettingsResponse> {
    const response = await this.request('/settings');
    return OperationalSettingsResponseSchema.parse(response);
  }

  async updateOperationalSettings(
    data: OperationalSettingsUpdate
  ): Promise<OperationalSettingsResponse> {
    const response = await this.request('/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return OperationalSettingsResponseSchema.parse(response);
  }
}

// Create singleton instance
export const apiClient = new WireGuardApiClient();

export default apiClient;
