import { WireGuardApiClient } from './api-client';

describe('WireGuardApiClient - regenerateDeviceApiKey URL Formation', () => {
  let apiClient: WireGuardApiClient;
  let mockFetch: jest.Mock;

  beforeEach(() => {
    // Mock fetch to return basic Response objects
    mockFetch = jest.fn((url) => {
      if (url.includes('/api/csrf/token')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ token: 'mock-csrf-token' }),
          headers: new Headers({ 'content-type': 'application/json' }),
        }) as Response;
      }
      if (url.includes('/api/devices/test-device-id/regenerate-api-key')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ key_value: 'new-api-key' }),
          headers: new Headers({ 'content-type': 'application/json' }),
        }) as Response;
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        headers: new Headers({ 'content-type': 'application/json' }),
      }) as Response;
    });

    global.fetch = mockFetch;

    // Mock document.cookie to return a CSRF token (so ensureCsrfToken doesn't call fetch)
    const originalCookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
    Object.defineProperty(Document.prototype, 'cookie', {
      value: 'csrf_token=mock-csrf-token',
      writable: true,
    });

    apiClient = new WireGuardApiClient();

    // Restore original cookie property
    if (originalCookie) {
      Object.defineProperty(Document.prototype, 'cookie', originalCookie);
    }
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should call the regenerate endpoint and return the API key', async () => {
    const result = await apiClient.regenerateDeviceApiKey('test-device-id');

    expect(result).toEqual({ api_key: 'new-api-key' });

    const calls = mockFetch.mock.calls;
    const urls = calls.map((call) => call[0] as string);

    // Find the regenerate call
    const regenerateCall = urls.find((url) =>
      url.includes('/devices/test-device-id/regenerate-api-key')
    );
    expect(regenerateCall).toBeTruthy();
    expect(regenerateCall).toMatch(
      /\/api\/devices\/test-device-id\/regenerate-api-key$/
    );

    // The key test: verify no URL has a versioned prefix
    urls.forEach((url) => {
      expect(url).not.toMatch(/\/api\/v1\//);
    });
  });

  it('should use POST method for regenerate endpoint', async () => {
    await apiClient.regenerateDeviceApiKey('test-device-id');

    const calls = mockFetch.mock.calls;
    const regenerateCall = calls.find((call) =>
      (call[0] as string).includes('/devices/test-device-id/regenerate-api-key')
    );

    expect(regenerateCall).toBeTruthy();
    const options = regenerateCall![1] as RequestInit;
    expect(options.method).toBe('POST');
  });

  it('should redact sensitive fields in 422 logs', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    const errorPayload = JSON.stringify({
      detail: 'Invalid request',
      body: {
        private_key: 'secret-private-key',
        preshared_key: 'secret-psk',
      },
    });

    mockFetch.mockImplementation((url) => {
      if (url.includes('/api/devices')) {
        return Promise.resolve({
          ok: false,
          status: 422,
          text: () => Promise.resolve(errorPayload),
          headers: new Headers({ 'content-type': 'application/json' }),
        }) as Response;
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        headers: new Headers({ 'content-type': 'application/json' }),
      }) as Response;
    });

    await expect(
      apiClient.createDevice({
        network_id: 'net-1',
        location_id: 'loc-1',
        name: 'Device 1',
        enabled: true,
        external_endpoint_host: 'example.com',
        external_endpoint_port: 51820,
        private_key: 'secret-private-key',
        preshared_key: 'secret-psk',
      })
    ).rejects.toThrow('API request failed');

    const logCall = consoleError.mock.calls.find(
      (call) => call[0] === '422 Unprocessable Entity - Request Details:'
    );
    expect(logCall).toBeTruthy();
    expect(logCall?.[1]?.requestBody).toMatchObject({
      private_key: '[redacted]',
      preshared_key: '[redacted]',
    });

    consoleError.mockRestore();
  });
});
