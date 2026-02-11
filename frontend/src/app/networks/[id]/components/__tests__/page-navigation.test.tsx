import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import NetworkConnectionsPage from '../../connections/page';
import NetworkExportPage from '../../export/page';
import NetworkEditPage from '../../edit/page';

jest.mock('next/navigation', () => ({
  useParams: jest.fn(() => ({ id: 'test-network-id', deviceId: 'test-device-id' })),
  useRouter: jest.fn(),
}));

jest.mock('@/contexts/unlock-context', () => ({
  useUnlock: () => ({
    isUnlocked: true,
  }),
}));

jest.mock('@/components/breadcrumb-provider', () => ({
  useBreadcrumbs: () => ({
    setLabel: jest.fn(),
  }),
}));

jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    getNetwork: jest.fn(),
    listDevices: jest.fn(),
    listDevicePeerLinks: jest.fn(),
    getDevice: jest.fn(),
    listLocations: jest.fn(),
    generateWireGuardPresharedKey: jest.fn(),
  },
}));

import apiClient from '@/lib/api-client';

const mockPush = jest.fn();

describe('Back button navigation behavior', () => {
  const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      back: jest.fn(),
    });
  });

  describe('Network connections page', () => {
    beforeEach(() => {
      mockedApiClient.getNetwork.mockResolvedValue({
        id: 'test-network-id',
        name: 'Test Network',
        network_cidr: '10.0.0.0/24',
        location_count: 2,
        device_count: 3,
        persistent_keepalive: 25,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      mockedApiClient.listDevices.mockResolvedValue([]);
      mockedApiClient.listDevicePeerLinks.mockResolvedValue([]);
    });

    it('navigates to network detail when clicking "Back to Network"', async () => {
      render(<NetworkConnectionsPage />);

      await waitFor(() => {
        expect(screen.getByText('Test Network')).toBeInTheDocument();
      });

      const backButton = screen.getByRole('button', { name: /back to network/i });
      await userEvent.click(backButton);

      expect(mockPush).toHaveBeenCalledWith('/networks/test-network-id');
      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });

  describe('Network export page', () => {
    beforeEach(() => {
      mockedApiClient.getNetwork.mockResolvedValue({
        id: 'test-network-id',
        name: 'Test Network',
        network_cidr: '10.0.0.0/24',
        location_count: 2,
        device_count: 3,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    it('navigates to network detail when clicking "Back to Network"', async () => {
      render(<NetworkExportPage />);

      await waitFor(() => {
        expect(screen.getByText('Export Network Configs')).toBeInTheDocument();
      });

      const backButton = screen.getByRole('button', { name: /back to network/i });
      await userEvent.click(backButton);

      expect(mockPush).toHaveBeenCalledWith('/networks/test-network-id');
      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });

  describe('Network edit page', () => {
    beforeEach(() => {
      mockedApiClient.getNetwork.mockResolvedValue({
        id: 'test-network-id',
        name: 'Test Network',
        network_cidr: '10.0.0.0/24',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    it('navigates to network detail when clicking "Back to Network"', async () => {
      render(<NetworkEditPage />);

      await waitFor(() => {
        expect(screen.getByText('Edit Network')).toBeInTheDocument();
      });

      const backButton = screen.getByRole('button', { name: /back to network/i });
      await userEvent.click(backButton);

      expect(mockPush).toHaveBeenCalledWith('/networks/test-network-id');
      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });
});
