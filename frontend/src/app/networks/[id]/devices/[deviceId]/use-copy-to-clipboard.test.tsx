import { renderHook, act } from '@testing-library/react';
import { useCopyToClipboard } from './use-copy-to-clipboard';

Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(),
  },
});

describe('useCopyToClipboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should copy text to clipboard and show toast', async () => {
    const mockWriteText = jest.mocked(navigator.clipboard.writeText);
    mockWriteText.mockResolvedValue(undefined);

    const { result } = renderHook(() => useCopyToClipboard());

    await act(async () => {
      await result.current.copyToClipboard('test text', 'Test Type');
    });

    expect(mockWriteText).toHaveBeenCalledWith('test text');
    expect(result.current.isCopied).toBe(false);
  });

  it('should set copied state for API Key type', async () => {
    const mockWriteText = jest.mocked(navigator.clipboard.writeText);
    mockWriteText.mockResolvedValue(undefined);

    const { result } = renderHook(() => useCopyToClipboard());

    await act(async () => {
      await result.current.copyToClipboard('api key', 'API Key');
    });

    expect(result.current.isCopied).toBe(true);

    act(() => {
      jest.advanceTimersByTime(2000);
    });

    expect(result.current.isCopied).toBe(false);
  });

  it('should properly clean up timeout on unmount', async () => {
    const mockWriteText = jest.mocked(navigator.clipboard.writeText);
    mockWriteText.mockResolvedValue(undefined);
    const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');

    const { result, unmount } = renderHook(() => useCopyToClipboard());

    await act(async () => {
      await result.current.copyToClipboard('api key', 'API Key');
    });

    expect(result.current.isCopied).toBe(true);

    unmount();

    expect(clearTimeoutSpy).toHaveBeenCalled();
    clearTimeoutSpy.mockRestore();
  });

  it('should handle clipboard errors', async () => {
    const mockWriteText = jest.mocked(navigator.clipboard.writeText);
    mockWriteText.mockRejectedValue(new Error('Clipboard error'));

    const { result } = renderHook(() => useCopyToClipboard());

    await act(async () => {
      await result.current.copyToClipboard('test text', 'Test Type');
    });

    expect(result.current.isCopied).toBe(false);
  });
});
