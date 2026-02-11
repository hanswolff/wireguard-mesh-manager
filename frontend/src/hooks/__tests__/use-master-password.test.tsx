import { renderHook, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { useMasterPassword } from '../use-master-password';
import { UnlockProvider, useUnlock } from '@/contexts/unlock-context';
import { toast } from '@/components/ui/use-toast';

// Mock dependencies
jest.mock('@/contexts/unlock-context', () => ({
  useUnlock: jest.fn(),
  UnlockProvider: ({ children }: { children: ReactNode }) => children,
}));
jest.mock('@/components/ui/use-toast');

const mockUseUnlock = useUnlock as jest.MockedFunction<typeof useUnlock>;
const mockToast = toast as jest.MockedFunction<typeof toast>;

describe('useMasterPassword', () => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <UnlockProvider>{children}</UnlockProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock state
    mockUseUnlock.mockReturnValue({
      isUnlocked: false,
      isChecking: false,
      status: null,
      unlock: jest.fn(),
      lock: jest.fn(),
      refreshStatus: jest.fn(),
      extendTtl: jest.fn(),
      requireUnlock: jest.fn(() => false),
    });
  });

  it('should return correct initial state', () => {
    const { result } = renderHook(() => useMasterPassword(), { wrapper });

    expect(result.current.showUnlockModal).toBe(false);
    expect(result.current.isUnlocked).toBe(false);
    expect(result.current.isChecking).toBe(false);
  });

  it('should show unlock modal when not unlocked', () => {
    const { result } = renderHook(() => useMasterPassword(), { wrapper });

    act(() => {
      result.current.requireUnlock();
    });

    expect(result.current.showUnlockModal).toBe(true);
  });

  it('should execute callback when unlocked', () => {
    const callback = jest.fn();
    const onSuccess = jest.fn();

    mockUseUnlock.mockReturnValue({
      isUnlocked: true,
      isChecking: false,
      status: null,
      unlock: jest.fn(),
      lock: jest.fn(),
      refreshStatus: jest.fn(),
      extendTtl: jest.fn(),
      requireUnlock: jest.fn(() => true),
    });

    const { result } = renderHook(() => useMasterPassword({ onSuccess }), {
      wrapper,
    });

    act(() => {
      result.current.requireUnlock(callback);
    });

    expect(callback).toHaveBeenCalled();
    expect(onSuccess).toHaveBeenCalled();
    expect(result.current.showUnlockModal).toBe(false);
  });

  it('should handle unlock success', () => {
    const onSuccess = jest.fn();

    const { result } = renderHook(() => useMasterPassword({ onSuccess }), {
      wrapper,
    });

    act(() => {
      result.current.handleUnlockSuccess();
    });

    expect(result.current.showUnlockModal).toBe(false);
    expect(onSuccess).toHaveBeenCalled();
  });

  it('should handle unlock failure with custom message', () => {
    const onFailure = jest.fn();
    const customMessage = 'Custom failure message';

    const { result } = renderHook(
      () => useMasterPassword({ onFailure, customMessage }),
      { wrapper }
    );

    act(() => {
      result.current.handleUnlockFailure();
    });

    expect(result.current.showUnlockModal).toBe(false);
    expect(onFailure).toHaveBeenCalled();
    expect(mockToast).toHaveBeenCalledWith({
      title: 'Authentication Required',
      description: customMessage,
      variant: 'destructive',
    });
  });

  it('should handle unlock failure without custom message', () => {
    const onFailure = jest.fn();

    const { result } = renderHook(() => useMasterPassword({ onFailure }), {
      wrapper,
    });

    act(() => {
      result.current.handleUnlockFailure();
    });

    expect(result.current.showUnlockModal).toBe(false);
    expect(onFailure).toHaveBeenCalled();
    expect(mockToast).not.toHaveBeenCalled();
  });

  it('should return false while checking', () => {
    mockUseUnlock.mockReturnValue({
      isUnlocked: false,
      isChecking: true,
      status: null,
      unlock: jest.fn(),
      lock: jest.fn(),
      refreshStatus: jest.fn(),
      extendTtl: jest.fn(),
      requireUnlock: jest.fn(() => false),
    });

    const { result } = renderHook(() => useMasterPassword(), { wrapper });
    const callback = jest.fn();

    act(() => {
      void result.current.requireUnlock(callback);
    });

    expect(callback).not.toHaveBeenCalled();
    expect(result.current.showUnlockModal).toBe(false);
  });

  it('should update modal state', () => {
    const { result } = renderHook(() => useMasterPassword(), { wrapper });

    act(() => {
      result.current.setShowUnlockModal(true);
    });

    expect(result.current.showUnlockModal).toBe(true);

    act(() => {
      result.current.setShowUnlockModal(false);
    });

    expect(result.current.showUnlockModal).toBe(false);
  });
});
