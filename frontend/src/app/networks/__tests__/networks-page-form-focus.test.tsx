import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NetworksPage from '../page';
import apiClient from '@/lib/api-client';

jest.mock('@/contexts/unlock-context', () => ({
  useUnlock: () => ({
    isUnlocked: true,
  }),
}));

jest.mock('@/lib/api-client', () => ({
  __esModule: true,
  default: {
    listNetworks: jest.fn(),
    createNetwork: jest.fn(),
    updateNetwork: jest.fn(),
    deleteNetwork: jest.fn(),
    generateWireGuardPresharedKey: jest.fn(),
  },
}));

describe('NetworksPage dialog validation focus', () => {
  const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

  beforeEach(() => {
    mockedApiClient.listNetworks.mockResolvedValue([]);
  });

  it('focuses the first invalid field when creating a network', async () => {
    render(<NetworksPage />);

    await waitFor(() =>
      expect(
        screen.getAllByRole('button', { name: /create network/i }).length
      ).toBeGreaterThan(0)
    );

    const user = userEvent.setup();
    const createButtons = screen.getAllByRole('button', {
      name: /create network/i,
    });
    await user.click(createButtons[0]);

    const dialog = screen.getByRole('dialog', { name: /create new network/i });
    const dialogButton = within(dialog).getByRole('button', {
      name: /create network/i,
    });

    await user.click(dialogButton);

    const nameInput = within(dialog).getByLabelText(/name \*/i);
    expect(nameInput).toHaveFocus();
  });
});
