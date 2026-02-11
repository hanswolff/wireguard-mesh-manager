import { renderHook, waitFor, act } from '@testing-library/react';
import { toast } from '@/components/ui/use-toast';
import { useConfigLint } from '../use-config-lint';
import apiClient, {
  type WireGuardNetworkResponse,
  type ConfigLintResponse,
} from '@/lib/api-client';

jest.mock('@/components/ui/use-toast', () => ({
  toast: jest.fn(),
}));

jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    listLocations: jest.fn(),
    listDevices: jest.fn(),
    lintNetworkConfig: jest.fn(),
  },
}));

const mockNetwork: WireGuardNetworkResponse = {
  id: 'test-network-id',
  name: 'Test Network',
  description: 'Test description',
  network_cidr: '192.168.1.0/24',
  dns_servers: '8.8.8.8,8.8.4.4',
  mtu: 1420,
  persistent_keepalive: 25,
  location_count: 2,
  device_count: 3,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockLocations = [
  {
    id: 'loc1',
    name: 'Location 1',
    description: 'Test location',
    external_endpoint: '192.168.1.1:51820',
    network_id: 'test-network-id',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

const mockDevices = [
  {
    id: 'dev1',
    name: 'Device 1',
    description: 'Test device',
    wireguard_ip: '192.168.1.2',
    public_key: 'device-public-key',
    preshared_key_encrypted: null,
    enabled: true,
    network_id: 'test-network-id',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

const mockLintResults: ConfigLintResponse = {
  valid: true,
  summary: 'Configuration is valid',
  issues: [],
  issue_count: {},
};

describe('useConfigLint', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.listLocations as jest.Mock).mockResolvedValue(mockLocations);
    (apiClient.listDevices as jest.Mock).mockResolvedValue(mockDevices);
    (apiClient.lintNetworkConfig as jest.Mock).mockResolvedValue(
      mockLintResults
    );
  });

  it('should not perform lint when network is null', () => {
    const { result } = renderHook(() => useConfigLint(null));

    expect(result.current.lintResults).toBeNull();
    expect(result.current.lintLoading).toBe(false);
    expect(apiClient.listLocations).not.toHaveBeenCalled();
    expect(apiClient.listDevices).not.toHaveBeenCalled();
    expect(apiClient.lintNetworkConfig).not.toHaveBeenCalled();
  });

  it('should perform lint when network is provided', async () => {
    const { result } = renderHook(() => useConfigLint(mockNetwork));

    expect(result.current.lintLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.lintLoading).toBe(false);
    });

    expect(apiClient.listLocations).toHaveBeenCalledWith({
      network_id: mockNetwork.id,
    });
    expect(apiClient.listDevices).toHaveBeenCalledWith({
      network_id: mockNetwork.id,
    });
    expect(apiClient.lintNetworkConfig).toHaveBeenCalledWith(
      expect.objectContaining({
        network_cidr: mockNetwork.network_cidr,
        dns_servers: mockNetwork.dns_servers,
        mtu: mockNetwork.mtu,
        persistent_keepalive: mockNetwork.persistent_keepalive,
        locations: expect.arrayContaining([
          expect.objectContaining({
            name: 'Location 1',
            description: 'Test location',
            external_endpoint: '192.168.1.1:51820',
          }),
        ]),
        devices: expect.arrayContaining([
          expect.objectContaining({
            name: 'Device 1',
            description: 'Test device',
            wireguard_ip: '192.168.1.2',
            public_key: 'device-public-key',
            preshared_key: null,
            enabled: true,
          }),
        ]),
      })
    );

    expect(result.current.lintResults).toEqual(mockLintResults);
  });

  it('should handle errors gracefully', async () => {
    const errorMessage = 'Failed to validate config';
    (apiClient.lintNetworkConfig as jest.Mock).mockRejectedValue(
      new Error(errorMessage)
    );

    const { result } = renderHook(() => useConfigLint(mockNetwork));

    await waitFor(() => {
      expect(result.current.lintLoading).toBe(false);
    });

    expect(toast).toHaveBeenCalledWith({
      title: 'Config Lint Failed',
      description: errorMessage,
      variant: 'destructive',
    });

    expect(result.current.lintResults).toBeNull();
  });

  it('should allow manual refresh', async () => {
    const { result } = renderHook(() => useConfigLint(mockNetwork));

    await waitFor(() => {
      expect(result.current.lintLoading).toBe(false);
    });

    jest.clearAllMocks();

    await act(async () => {
      await result.current.performConfigLint();
    });

    expect(apiClient.listLocations).toHaveBeenCalledTimes(1);
    expect(apiClient.listDevices).toHaveBeenCalledTimes(1);
    expect(apiClient.lintNetworkConfig).toHaveBeenCalledTimes(1);
  });

  it('should not perform manual refresh when network is null', async () => {
    const { result } = renderHook(() => useConfigLint(null));

    await act(async () => {
      await result.current.performConfigLint();
    });

    expect(apiClient.listLocations).not.toHaveBeenCalled();
    expect(apiClient.listDevices).not.toHaveBeenCalled();
    expect(apiClient.lintNetworkConfig).not.toHaveBeenCalled();
  });
});
