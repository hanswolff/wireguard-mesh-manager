/**
 * Helper to create a mocked API client instance
 */

import type {
  MasterPasswordStatusResponse,
  MasterPasswordUnlockRequest,
  MasterPasswordUnlockResponse,
  MasterPasswordExtendTTLRequest,
  MasterPasswordExtendTTLResponse,
  KeyRotationEstimate,
  PasswordValidation,
  PasswordStrengthValidation,
  PasswordPolicy,
  MasterPasswordRotate,
  KeyRotationStatus,
  HealthCheckResponse,
  MetricsResponse,
  AuditEventList,
  AuditEventParams,
  AuditExportParams,
  AuditStatistics,
  WireGuardNetworkCreate,
  WireGuardNetworkUpdate,
  WireGuardNetworkListItem,
  WireGuardNetworkResponse,
  LocationCreate,
  LocationUpdate,
  LocationResponse,
  DeviceCreate,
  DeviceUpdate,
  DeviceResponse,
  DeviceConfigResponse,
  ExportRequest,
  ExportData,
  ConfigLintRequest,
  ConfigLintResponse,
} from '@/lib/api-client';

// Create a mock API client that preserves method signatures
const createMockApiClient = () => {
  const mockClient = {
    // Health
    getHealth: jest.fn<[], Promise<HealthCheckResponse>>(),
    getMetrics: jest.fn<[], Promise<MetricsResponse>>(),

    // Master Password
    getMasterPasswordStatus: jest.fn<[], Promise<MasterPasswordStatusResponse>>(),
    unlockMasterPassword: jest.fn<[MasterPasswordUnlockRequest], Promise<MasterPasswordUnlockResponse>>(),
    lockMasterPassword: jest.fn<[], Promise<MasterPasswordUnlockResponse>>(),
    extendMasterPasswordTTL: jest.fn<[MasterPasswordExtendTTLRequest], Promise<MasterPasswordExtendTTLResponse>>(),
    refreshMasterPasswordAccess: jest.fn<[], Promise<{ message: string }>>(),

    // Key Rotation
    getRotationEstimate: jest.fn<[], Promise<KeyRotationEstimate>>(),
    validateCurrentPassword: jest.fn<[string], Promise<PasswordValidation>>(),
    validatePassword: jest.fn<[string], Promise<PasswordStrengthValidation>>(),
    getPasswordPolicy: jest.fn<[], Promise<PasswordPolicy>>(),
    rotateMasterPassword: jest.fn<[MasterPasswordRotate], Promise<KeyRotationStatus>>(),

    // Audit
    getAuditEvents: jest.fn<[AuditEventParams?], Promise<AuditEventList>>(),
    getAuditStatistics: jest.fn<[], Promise<AuditStatistics>>(),
    exportAuditEvents: jest.fn<[AuditExportParams], Promise<string>>(),
    getRetentionInfo: jest.fn<[], Promise<{ retention_days: number; cutoff_date: string; expired_events_count: number; export_batch_size: number }>>(),
    cleanupExpiredEvents: jest.fn<[], Promise<{ events_deleted: number; cutoff_date: string; retention_days: number }>>(),

    // Networks
    listNetworks: jest.fn<[], Promise<WireGuardNetworkListItem[]>>(),
    getNetwork: jest.fn<[string], Promise<WireGuardNetworkResponse>>(),
    createNetwork: jest.fn<[WireGuardNetworkCreate], Promise<WireGuardNetworkResponse>>(),
    updateNetwork: jest.fn<[string, WireGuardNetworkUpdate], Promise<WireGuardNetworkResponse>>(),
    deleteNetwork: jest.fn<[string], Promise<{ message: string }>>(),

    // Locations
    listLocations: jest.fn<[], Promise<LocationResponse[]>>(),
    getLocation: jest.fn<[string], Promise<LocationResponse>>(),
    createLocation: jest.fn<[LocationCreate], Promise<LocationResponse>>(),
    updateLocation: jest.fn<[string, LocationUpdate], Promise<LocationResponse>>(),
    deleteLocation: jest.fn<[string], Promise<{ message: string }>>(),

    // Devices
    listDevices: jest.fn<[], Promise<DeviceResponse[]>>(),
    getDevice: jest.fn<[string], Promise<DeviceResponse>>(),
    createDevice: jest.fn<[DeviceCreate], Promise<DeviceResponse>>(),
    updateDevice: jest.fn<[string, DeviceUpdate], Promise<DeviceResponse>>(),
    deleteDevice: jest.fn<[string], Promise<{ message: string }>>(),
    regenerateDeviceApiKey: jest.fn<[string], Promise<{ api_key: string }>>(),

    // Device Config
    getDeviceConfig: jest.fn<[string, { format?: 'wg' }?], Promise<DeviceConfigResponse>>(),
    getAdminDeviceConfig: jest.fn<[string, { format?: 'wg' | 'json' | 'mobile'; platform?: string }?], Promise<DeviceConfigResponse>>(),
    downloadAdminDeviceConfig: jest.fn<[string], Promise<void>>(),
    getDeviceConfigByApiKey: jest.fn<
      [string, string, { format?: 'wg' }?],
      Promise<DeviceConfigResponse>
    >(),

    // Export
    exportNetworks: jest.fn<[ExportRequest], Promise<ExportData>>(),
    downloadExport: jest.fn<[ExportRequest], Promise<Blob>>(),
    downloadNetworkConfigs: jest.fn<
      [
        string,
        { format?: 'wg' | 'json' | 'mobile'; includePresharedKeys?: boolean }?
      ],
      Promise<Blob>
    >(),

    // Config Lint
    lintNetworkConfig: jest.fn<[ConfigLintRequest], Promise<ConfigLintResponse>>(),
  } as typeof jest;

  return mockClient;
};

describe('createMockApiClient', () => {
  it('should create a mock API client with all required methods', () => {
    const mockClient = createMockApiClient();

    expect(mockClient.getMasterPasswordStatus).toBeDefined();
    expect(mockClient.unlockMasterPassword).toBeDefined();
    expect(mockClient.lockMasterPassword).toBeDefined();
    expect(mockClient.extendMasterPasswordTTL).toBeDefined();
    expect(mockClient.getRotationEstimate).toBeDefined();
    expect(mockClient.validateCurrentPassword).toBeDefined();
    expect(mockClient.validatePassword).toBeDefined();
    expect(mockClient.getPasswordPolicy).toBeDefined();
    expect(mockClient.rotateMasterPassword).toBeDefined();
  });

  it('should allow setting mock return values', () => {
    const mockClient = createMockApiClient();

    mockClient.getMasterPasswordStatus.mockResolvedValue({
      is_unlocked: false,
      expires_at: null,
      ttl_seconds: 0,
      idle_ttl_seconds: 0,
      access_count: 0,
      last_access: null,
    });

    expect(mockClient.getMasterPasswordStatus).toBeDefined();
  });
});

export { createMockApiClient };
