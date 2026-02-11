import { render, screen, waitFor, findByText } from '@testing-library/react';
import '@testing-library/jest-dom';

import { apiClient } from '@/lib/api-client';

jest.mock('@/lib/api-client');

const mockGetOperationalSettings = apiClient.getOperationalSettings as jest.MockedFunction<
  typeof apiClient.getOperationalSettings
>;

jest.mock('@/components/global-states', () => ({
  GlobalStateWrapper: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

jest.mock('@/contexts/unlock-context', () => ({
  UnlockProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  useUnlock: () => ({ isUnlocked: true }),
}));

import SettingsPage from '../page';

describe('Settings Page', () => {
  const renderPage = async () => {
    render(<SettingsPage />);
    await waitFor(() =>
      expect(mockGetOperationalSettings).toHaveBeenCalled()
    );
  };

  beforeEach(() => {
    mockGetOperationalSettings.mockResolvedValue({
      max_request_size: 10485760,
      request_timeout: 30,
      max_json_depth: 20,
      max_string_length: 10000,
      max_items_per_array: 1000,
      rate_limit_api_key_window: 300,
      rate_limit_api_key_max_requests: 1000,
      rate_limit_ip_window: 60,
      rate_limit_ip_max_requests: 100,
      audit_retention_days: 90,
      audit_export_batch_size: 1000,
      master_password_ttl_hours: 1,
      master_password_idle_timeout_minutes: 15,
      master_password_per_user_session: true,
      trusted_proxies: '127.0.0.1, ::1',
      cors_origins:
        'http://localhost:3000, https://wireguard-mesh-manager.example.com',
      cors_allow_credentials: true,
    });
  });

  it('should render without crashing', async () => {
    await expect(renderPage()).resolves.not.toThrow();
  });

  it('should render the page title', async () => {
    await renderPage();

    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('should render CORS Configuration card', async () => {
    await renderPage();

    expect(await screen.findByText('CORS Configuration')).toBeInTheDocument();
    expect(await screen.findByText('Allowed Origins')).toBeInTheDocument();
  });

  it('should render Security Configuration card', async () => {
    await renderPage();

    expect(await screen.findByText('Security Configuration')).toBeInTheDocument();
    expect(await screen.findByText('Trusted Proxies')).toBeInTheDocument();
  });

  it('should render Audit Configuration card', async () => {
    await renderPage();

    expect(
      await screen.findByText('Audit & Logging Configuration')
    ).toBeInTheDocument();
  });

  it('should render Master Password Cache card', async () => {
    await renderPage();

    expect(
      await screen.findByText('Master Password Cache Configuration')
    ).toBeInTheDocument();
  });

  it('should render CORS origins list with mock data', async () => {
    await renderPage();

    // Should display mock CORS origins
    expect(await screen.findByText('http://localhost:3000')).toBeInTheDocument();
    expect(
      await screen.findByText('https://wireguard-mesh-manager.example.com')
    ).toBeInTheDocument();
  });

  it('should render trusted proxies list with mock data', async () => {
    await renderPage();

    // Should display mock trusted proxies
    expect(await screen.findByText('127.0.0.1')).toBeInTheDocument();
    expect(await screen.findByText('::1')).toBeInTheDocument();
  });
});
