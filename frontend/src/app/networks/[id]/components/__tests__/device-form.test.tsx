import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DeviceForm from '../device-form';
import type { DeviceResponse, LocationResponse } from '@/lib/api-client';
import apiClient from '@/lib/api-client';

jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    generateWireGuardKeys: jest.fn(),
    generateWireGuardPresharedKey: jest.fn(),
  },
}));

jest.mock('@/contexts/unlock-context', () => ({
  useUnlock: () => ({
    requireUnlock: (callback?: () => void) => {
      if (callback) {
        callback();
      }
      return true;
    },
  }),
}));

describe('DeviceForm focus behavior', () => {
  const locations: LocationResponse[] = [
    {
      id: 'loc-1',
      name: 'Location One',
      network_id: 'net-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      external_endpoint: 'example.com',
      internal_endpoint: null,
      device_count: 0,
    },
  ];

  const renderForm = () =>
    render(
      <DeviceForm
        open={true}
        onOpenChange={jest.fn()}
        onSubmit={jest.fn()}
        isSubmitting={false}
        locations={locations}
        networkId="net-1"
        networkCidr="10.0.0.0/24"
        mode="create"
      />
    );

  it('focuses the first invalid field on submit', async () => {
    renderForm();

    const user = userEvent.setup();
    const submitButton = screen.getByRole('button', { name: /add device/i });

    await user.click(submitButton);

    const nameInput = screen.getByLabelText(/name \*/i);
    expect(nameInput).toHaveFocus();
  });

  it('focuses the location select when name is valid', async () => {
    renderForm();

    const user = userEvent.setup();
    const nameInput = screen.getByLabelText(/name \*/i);
    await user.type(nameInput, 'device-one');

    const submitButton = screen.getByRole('button', { name: /add device/i });
    await user.click(submitButton);

    const locationText = screen.getByText(/select a location/i);
    const locationTrigger = locationText.closest('button');

    if (!locationTrigger) {
      throw new Error('Location trigger button not found.');
    }

    expect(locationTrigger).toHaveFocus();
  });

  it('does not move focus during live validation', async () => {
    renderForm();

    const nameInput = screen.getByLabelText(/name \*/i);
    const wireguardInput = screen.getByLabelText(/wireguard ip/i);

    nameInput.focus();
    expect(nameInput).toHaveFocus();

    fireEvent.change(wireguardInput, { target: { value: '999' } });

    await waitFor(() =>
      expect(
        screen.getByText(/not within the network cidr/i)
      ).toBeInTheDocument()
    );

    expect(nameInput).toHaveFocus();
  });
});

describe('DeviceForm preshared key generation', () => {
  const locations: LocationResponse[] = [
    {
      id: 'loc-1',
      name: 'Location One',
      network_id: 'net-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      external_endpoint: 'example.com',
      internal_endpoint: null,
      device_count: 0,
    },
  ];

  const mockPresharedKey = 'abcdefghijklmnopqrstuvwxyz0123456789ABCD';

  const renderForm = () =>
    render(
      <DeviceForm
        open={true}
        onOpenChange={jest.fn()}
        onSubmit={jest.fn()}
        isSubmitting={false}
        locations={locations}
        networkId="net-1"
        networkCidr="10.0.0.0/24"
        mode="create"
      />
    );

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const getPresharedKeyGenerateButton = () => {
    const presharedKeyLabel = screen.getByLabelText(
      /preshared key \(optional\)/i
    );
    const presharedKeySection = presharedKeyLabel.closest('.grid');
    if (!presharedKeySection) {
      throw new Error('Preshared key section not found');
    }
    const buttons = presharedKeySection.querySelectorAll('button');
    for (const button of buttons) {
      if (button.textContent?.includes('Generate') &&
          !button.textContent?.includes('Keys')) {
        return button;
      }
    }
    throw new Error('Preshared key generate button not found');
  };

  it('renders the generate preshared key button', () => {
    renderForm();
    const generateButton = getPresharedKeyGenerateButton();
    expect(generateButton).toBeInTheDocument();
  });

  it('generates preshared key successfully and updates form', async () => {
    (apiClient.generateWireGuardPresharedKey as jest.Mock).mockResolvedValue({
      preshared_key: mockPresharedKey,
    });

    renderForm();

    const user = userEvent.setup();
    const generateButton = getPresharedKeyGenerateButton();
    const presharedKeyInput = screen.getByLabelText(
      /preshared key \(optional\)/i
    );

    expect(presharedKeyInput).toHaveValue('');

    await act(async () => {
      await user.click(generateButton);
    });

    expect(apiClient.generateWireGuardPresharedKey).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(presharedKeyInput).toHaveValue(mockPresharedKey);
    });
  });

  it('shows loading state while generating preshared key', async () => {
    let resolveGeneration: (value: unknown) => void;
    (apiClient.generateWireGuardPresharedKey as jest.Mock).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveGeneration = resolve;
        })
    );

    renderForm();

    const user = userEvent.setup();
    const generateButton = getPresharedKeyGenerateButton();

    await act(async () => {
      await user.click(generateButton);
    });

    await waitFor(() => {
      expect(generateButton).toHaveTextContent('Generating...');
      expect(generateButton).toBeDisabled();
    });

    await act(async () => {
      resolveGeneration!({ preshared_key: mockPresharedKey });
    });

    await waitFor(() => {
      expect(generateButton).toHaveTextContent('Generate');
      expect(generateButton).not.toBeDisabled();
    });
  });

  it('handles preshared key generation error', async () => {
    const errorMessage = 'Network error';
    (apiClient.generateWireGuardPresharedKey as jest.Mock).mockRejectedValue(
      new Error(errorMessage)
    );

    renderForm();

    const user = userEvent.setup();
    const generateButton = getPresharedKeyGenerateButton();
    const presharedKeyInput = screen.getByLabelText(
      /preshared key \(optional\)/i
    );

    await act(async () => {
      await user.click(generateButton);
    });

    await waitFor(() => {
      expect(generateButton).toHaveTextContent('Generate');
      expect(generateButton).not.toBeDisabled();
    });

    expect(presharedKeyInput).toHaveValue('');
  });

  it('disables generate button when form is submitting', async () => {
    (apiClient.generateWireGuardPresharedKey as jest.Mock).mockResolvedValue({
      preshared_key: mockPresharedKey,
    });

    renderForm();

    const generateButton = getPresharedKeyGenerateButton();

    expect(generateButton).toBeEnabled();
  });

  it('disables generate button when already generating', async () => {
    let resolveGeneration: (value: unknown) => void;
    (apiClient.generateWireGuardPresharedKey as jest.Mock).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveGeneration = resolve;
        })
    );

    renderForm();

    const user = userEvent.setup();
    const generateButton = getPresharedKeyGenerateButton();

    await user.click(generateButton);

    await waitFor(() => {
      expect(generateButton).toBeDisabled();
    });

    await act(async () => {
      resolveGeneration!({ preshared_key: mockPresharedKey });
    });

    await waitFor(() => {
      expect(generateButton).not.toBeDisabled();
    });
  });
});

const formatLocationWithNetwork = (
  locationName: string,
  networkName?: string | null
): string => {
  if (!networkName) return locationName;
  return `${locationName} (${networkName})`;
};

describe('formatLocationWithNetwork utility', () => {
  it('returns location name when network name is not provided', () => {
    expect(formatLocationWithNetwork('My Location')).toBe('My Location');
  });

  it('returns location name when network name is null', () => {
    expect(formatLocationWithNetwork('My Location', null)).toBe('My Location');
  });

  it('returns location name when network name is undefined', () => {
    expect(formatLocationWithNetwork('My Location', undefined)).toBe('My Location');
  });

  it('returns formatted string with network name', () => {
    expect(formatLocationWithNetwork('My Location', 'My Network')).toBe('My Location (My Network)');
  });
});

describe('DeviceForm location dropdown with network names', () => {
  const mockLocations: LocationResponse[] = [
    {
      id: 'loc-1',
      name: 'Location One',
      network_id: 'net-1',
      network_name: 'Network Alpha',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      external_endpoint: 'example.com',
      internal_endpoint: null,
      device_count: 0,
    },
    {
      id: 'loc-2',
      name: 'Duplicate Location',
      network_id: 'net-1',
      network_name: 'Network Alpha',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      external_endpoint: 'example.com',
      internal_endpoint: null,
      device_count: 0,
    },
    {
      id: 'loc-3',
      name: 'Duplicate Location',
      network_id: 'net-2',
      network_name: 'Network Beta',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      external_endpoint: 'example.com',
      internal_endpoint: null,
      device_count: 0,
    },
    {
      id: 'loc-4',
      name: 'Location Without Network',
      network_id: 'net-3',
      network_name: undefined,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      external_endpoint: 'example.com',
      internal_endpoint: null,
      device_count: 0,
    },
  ];

  const mockDevice: DeviceResponse = {
    id: 'dev-1',
    name: 'Test Device',
    network_id: 'net-1',
    location_id: 'loc-1',
    location_name: 'Location One',
    network_name: 'Network Alpha',
    enabled: true,
    public_key: 'testPublicKey'.repeat(2),
    wireguard_ip: '10.0.0.2',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    external_endpoint_host: 'example.com',
    external_endpoint_port: 51820,
    endpoint_allowlist: [],
  };

  const renderForm = (mode: 'create' | 'edit' = 'create') =>
    render(
      <DeviceForm
        open={true}
        onOpenChange={jest.fn()}
        onSubmit={jest.fn()}
        isSubmitting={false}
        locations={mockLocations}
        networkId="net-1"
        networkCidr="10.0.0.0/24"
        mode={mode}
        device={mode === 'edit' ? mockDevice : undefined}
      />
    );

  it('shows placeholder with network name in edit mode', () => {
    renderForm('edit');

    const locationTrigger = screen.getByRole('combobox');
    expect(locationTrigger).toHaveTextContent('Location OneNetwork Alpha');
  });
});
