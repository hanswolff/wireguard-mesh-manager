import { renderHook, waitFor, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { useUnlock, UnlockProvider } from '../unlock-context';
import { toast } from '@/components/ui/use-toast';
import apiClient from '@/lib/api-client';

// Mock dependencies
jest.mock('@/lib/api-client');
jest.mock('@/components/ui/use-toast');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;
const mockToast = toast as jest.MockedFunction<typeof toast>;

describe('UnlockContext', () => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <UnlockProvider>{children}</UnlockProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
    window.sessionStorage.setItem('wmm.master_session_token', 'test_token');

    // Default successful API responses
    mockApiClient.getMasterPasswordStatus.mockResolvedValue({
      is_unlocked: false,
      expires_at: null,
      ttl_seconds: 0,
      idle_ttl_seconds: 0,
      access_count: 0,
      last_access: null,
    });

    mockApiClient.unlockMasterPassword.mockResolvedValue({
      success: true,
      message: 'Unlocked successfully',
      session_token: 'session-token',
    });

    mockApiClient.lockMasterPassword.mockResolvedValue({
      success: true,
      message: 'Locked successfully',
    });

    mockApiClient.extendMasterPasswordTTL.mockResolvedValue({
      success: true,
      message: 'TTL extended successfully',
    });

    mockApiClient.isMasterPasswordUnlocked.mockResolvedValue({
      is_unlocked: false,
    });
  });

  afterEach(() => {
    window.sessionStorage.removeItem('wmm.master_session_token');
    window.localStorage.removeItem('wmm.master_session_token');
  });

  it('should initialize with locked state', async () => {
    const { result } = renderHook(() => useUnlock(), { wrapper });

    expect(result.current.isChecking).toBe(true);
    expect(result.current.isUnlocked).toBe(false);

    await waitFor(() => {
      expect(result.current.isChecking).toBe(false);
    });
  });

  it('should check unlock status on mount', async () => {
    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(mockApiClient.getMasterPasswordStatus).toHaveBeenCalledTimes(1);
      expect(result.current.isChecking).toBe(false);
    });
  });

  it('should unlock successfully', async () => {
    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(result.current.isChecking).toBe(false);
    });

    const success = await act(async () => {
      return await result.current.unlock('test-password', 2); // pragma: allowlist secret
    });

    expect(success).toBe(true);
    expect(mockApiClient.unlockMasterPassword).toHaveBeenCalledWith({
      master_password: 'test-password', // pragma: allowlist secret
      ttl_hours: 2,
    });
    expect(mockToast).toHaveBeenCalledWith({
      title: 'Unlocked',
      description: 'Master password cached successfully',
    });
  });

  it('should handle unlock failure', async () => {
    mockApiClient.unlockMasterPassword.mockResolvedValue({
      success: false,
      message: 'Invalid password',
    });

    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(result.current.isChecking).toBe(false);
    });

    const success = await act(async () => {
      return await result.current.unlock('wrong-password'); // pragma: allowlist secret
    });

    expect(success).toBe(false);
    expect(mockToast).toHaveBeenCalledWith({
      title: 'Unlock Failed',
      description: 'Invalid password',
      variant: 'destructive',
    });
  });

  it('should lock successfully', async () => {
    mockApiClient.getMasterPasswordStatus.mockResolvedValue({
      is_unlocked: true,
      expires_at: new Date(Date.now() + 3600000).toISOString(),
      ttl_seconds: 3600,
      idle_ttl_seconds: 1800,
      access_count: 1,
      last_access: new Date().toISOString(),
    });

    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(result.current.isUnlocked).toBe(true);
    });

    // After lock, update the mock to return locked state
    mockApiClient.getMasterPasswordStatus.mockResolvedValue({
      is_unlocked: false,
      expires_at: null,
      ttl_seconds: 0,
      idle_ttl_seconds: 0,
      access_count: 0,
      last_access: null,
    });

    await act(async () => {
      await result.current.lock();
    });

    expect(result.current.isUnlocked).toBe(false);
    expect(mockApiClient.lockMasterPassword).toHaveBeenCalled();
    expect(mockToast).toHaveBeenCalledWith({
      title: 'Locked',
      description: 'Master password cache cleared',
    });
  });

  it('should extend TTL successfully', async () => {
    mockApiClient.getMasterPasswordStatus.mockResolvedValue({
      is_unlocked: true,
      expires_at: new Date(Date.now() + 3600000).toISOString(),
      ttl_seconds: 3600,
      idle_ttl_seconds: 1800,
      access_count: 1,
      last_access: new Date().toISOString(),
    });

    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(result.current.isUnlocked).toBe(true);
    });

    const success = await act(async () => {
      return await result.current.extendTtl(1);
    });

    expect(success).toBe(true);
    expect(mockApiClient.extendMasterPasswordTTL).toHaveBeenCalledWith({
      additional_hours: 1,
    });
    expect(mockToast).toHaveBeenCalledWith({
      title: 'Extended',
      description: 'Master password cache extended by 1 hour(s)',
    });
  });

  it('should auto-lock when expired', async () => {
    const expiredDate = new Date(Date.now() - 3600000).toISOString();

    mockApiClient.getMasterPasswordStatus.mockResolvedValue({
      is_unlocked: true,
      expires_at: expiredDate,
      ttl_seconds: 3600,
      idle_ttl_seconds: 1800,
      access_count: 1,
      last_access: new Date().toISOString(),
    });

    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(result.current.isChecking).toBe(false);
    });

    // Should auto-lock even though API says unlocked
    expect(result.current.isUnlocked).toBe(false);
  });

  it('should handle requireUnlock correctly', async () => {
    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(result.current.isChecking).toBe(false);
    });

    // Should not execute callback when locked
    const callback = jest.fn();
    const canProceed = result.current.requireUnlock(callback);

    expect(canProceed).toBe(false);
    expect(callback).not.toHaveBeenCalled();
  });

  it('should execute callback when unlocked', async () => {
    mockApiClient.getMasterPasswordStatus.mockResolvedValue({
      is_unlocked: true,
      expires_at: new Date(Date.now() + 3600000).toISOString(),
      ttl_seconds: 3600,
      idle_ttl_seconds: 1800,
      access_count: 1,
      last_access: new Date().toISOString(),
    });

    const { result } = renderHook(() => useUnlock(), { wrapper });

    await waitFor(() => {
      expect(result.current.isUnlocked).toBe(true);
    });

    const callback = jest.fn();
    const canProceed = result.current.requireUnlock(callback);

    expect(canProceed).toBe(true);
    expect(callback).toHaveBeenCalled();
  });

  it('should return false when checking status', async () => {
    const { result } = renderHook(() => useUnlock(), { wrapper });

    // During initial check
    expect(result.current.isChecking).toBe(true);

    const callback = jest.fn();
    const canProceed = result.current.requireUnlock(callback);

    expect(canProceed).toBe(false);
    expect(callback).not.toHaveBeenCalled();

    await waitFor(() => {
      expect(result.current.isChecking).toBe(false);
    });
  });
});
