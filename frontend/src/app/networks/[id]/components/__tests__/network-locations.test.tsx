import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NetworkLocations from '../network-locations';
import apiClient from '@/lib/api-client';

jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    listLocations: jest.fn(),
    createLocation: jest.fn(),
    updateLocation: jest.fn(),
    deleteLocation: jest.fn(),
    generateWireGuardPresharedKey: jest.fn(),
  },
}));

describe('NetworkLocations dialog validation focus', () => {
  const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

  beforeEach(() => {
    mockedApiClient.listLocations.mockResolvedValue([]);
  });

  it('focuses the first invalid field when creating a location', async () => {
    render(<NetworkLocations networkId="net-1" />);

    await waitFor(() =>
      expect(
        screen.getAllByRole('button', { name: /add location/i }).length
      ).toBeGreaterThan(0)
    );

    const user = userEvent.setup();
    const addButtons = screen.getAllByRole('button', { name: /add location/i });
    await user.click(addButtons[0]);

    const dialog = screen.getByRole('dialog', { name: /add new location/i });
    const dialogButton = within(dialog).getByRole('button', {
      name: /add location/i,
    });

    await user.click(dialogButton);

    const nameInput = within(dialog).getByLabelText(/name \*/i);
    expect(nameInput).toHaveFocus();
  });
});
