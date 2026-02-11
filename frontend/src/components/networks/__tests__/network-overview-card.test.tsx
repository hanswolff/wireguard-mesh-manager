import { render, screen } from '@testing-library/react';
import { NetworkOverviewCard } from '../network-overview-card';
import type { WireGuardNetworkResponse } from '@/lib/api-client';

const mockNetwork: WireGuardNetworkResponse = {
  id: '1',
  name: 'Test Network',
  description: 'Test Description',
  network_cidr: '10.0.0.0/24',
  dns_servers: '8.8.8.8,8.8.4.4',
  mtu: 1420,
  persistent_keepalive: 25,
  location_count: 2,
  device_count: 3,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('NetworkOverviewCard', () => {
  it('should display network overview correctly', () => {
    render(<NetworkOverviewCard network={mockNetwork} />);

    expect(screen.getByText('Network Overview')).toBeInTheDocument();
    expect(
      screen.getByText('Summary of devices that will be included in the export')
    ).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Devices')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Locations')).toBeInTheDocument();
    expect(screen.getByText('10.0.0.0/24')).toBeInTheDocument();
    expect(screen.getByText('Network CIDR')).toBeInTheDocument();
  });

  it('should have proper styling for device count', () => {
    render(<NetworkOverviewCard network={mockNetwork} />);

    const deviceCount = screen.getByText('3');
    expect(deviceCount).toHaveClass('text-2xl', 'font-bold', 'text-primary');
  });

  it('should have proper styling for location count', () => {
    render(<NetworkOverviewCard network={mockNetwork} />);

    const locationCount = screen.getByText('2');
    expect(locationCount).toHaveClass('text-2xl', 'font-bold', 'text-primary');
  });
});
