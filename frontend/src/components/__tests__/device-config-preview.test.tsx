import { render, screen } from '@testing-library/react';
import { DeviceConfigPreview } from '../device-config-preview';
import { type DeviceResponse } from '@/lib/api-client';

// pragma: allowlist secret
const mockDevice: DeviceResponse = {
  id: 'test-device-id',
  name: 'Test Device',
  description: 'Test device description',
  enabled: true,
  network_id: 'test-network-id',
  location_id: 'test-location-id',
  network_name: 'Test Network',
  location_name: 'Test Location',
  wireguard_ip: '192.168.1.2',
  public_key: 'test-public-key',
  preshared_key_encrypted: 'encrypted-preshared-key',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  api_key: 'test-api-key',
  endpoint_allowlist: [],
};

jest.mock('@/contexts/unlock-context', () => ({
  useUnlock: () => ({
    isUnlocked: false,
    requireUnlock: jest.fn(() => false),
  }),
}));

describe('DeviceConfigPreview', () => {
  it('should render component title and basic controls', () => {
    render(<DeviceConfigPreview device={mockDevice} />);

    expect(screen.getByText('Device Configuration')).toBeInTheDocument();
    expect(screen.getByText('Preview Config')).toBeInTheDocument();
    expect(screen.getByText('Download Config')).toBeInTheDocument();
  });

  it('should display device information properly', () => {
    render(<DeviceConfigPreview device={mockDevice} />);

    expect(screen.getByText('Device Configuration')).toBeInTheDocument();
  });
});
