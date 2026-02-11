import { renderHook, act, waitFor } from '@testing-library/react';
import { useCrud } from '../use-crud';
import { toast } from '@/components/ui/use-toast';

// Mock the toast hook
jest.mock('@/components/ui/use-toast', () => ({
  toast: jest.fn(),
}));

const mockToast = toast as jest.MockedFunction<typeof toast>;

describe('useCrud Hook', () => {
  const mockFetchFn = jest.fn();
  const mockCreateFn = jest.fn();
  const mockUpdateFn = jest.fn();
  const mockDeleteFn = jest.fn();
  const mockOnSuccess = jest.fn();

  const mockItems = [
    { id: '1', name: 'Item 1' },
    { id: '2', name: 'Item 2' },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with loading state', async () => {
    mockFetchFn.mockResolvedValue([]);

    const { result } = renderHook(() =>
      useCrud({
        fetchFn: mockFetchFn,
        entityName: 'test',
      })
    );

    expect(result.current.loading).toBe(true);
    expect(result.current.items).toEqual([]);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  it('should fetch items on mount', async () => {
    mockFetchFn.mockResolvedValue(mockItems);

    const { result } = renderHook(() =>
      useCrud({
        fetchFn: mockFetchFn,
        entityName: 'test',
      })
    );

    await waitFor(
      () => {
        expect(result.current.loading).toBe(false);
      },
      { timeout: 3000 }
    );

    expect(mockFetchFn).toHaveBeenCalled();
    expect(result.current.items).toEqual(mockItems);
  });

  it('should handle fetch error', async () => {
    const errorMessage = 'Fetch failed';
    mockFetchFn.mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() =>
      useCrud({
        fetchFn: mockFetchFn,
        entityName: 'test',
      })
    );

    await waitFor(
      () => {
        expect(result.current.loading).toBe(false);
      },
      { timeout: 3000 }
    );

    expect(mockToast).toHaveBeenCalledWith({
      title: 'Failed to fetch tests',
      description: errorMessage,
      variant: 'destructive',
    });
  });

  it('should create item successfully', async () => {
    const newItem = { name: 'New Item' };
    mockFetchFn.mockResolvedValue(mockItems);
    mockCreateFn.mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useCrud({
        fetchFn: mockFetchFn,
        createFn: mockCreateFn,
        entityName: 'test',
        onSuccess: mockOnSuccess,
      })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await result.current.create(newItem as any);
    });

    expect(mockCreateFn).toHaveBeenCalledWith(newItem);
    expect(mockToast).toHaveBeenCalledWith({
      title: 'test Created',
      description: 'New Item has been created successfully',
    });
    expect(mockOnSuccess).toHaveBeenCalledWith('create');
  });

  it('should handle create error', async () => {
    const newItem = { name: 'New Item' };
    const errorMessage = 'Create failed';
    mockFetchFn.mockResolvedValue(mockItems);
    mockCreateFn.mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() =>
      useCrud({
        fetchFn: mockFetchFn,
        createFn: mockCreateFn,
        entityName: 'test',
      })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await result.current.create(newItem as any);
    });

    expect(mockToast).toHaveBeenCalledWith({
      title: 'Create Failed',
      description: errorMessage,
      variant: 'destructive',
    });
  });

  it('should update item successfully', async () => {
    const updateData = { name: 'Updated Item' };
    mockFetchFn.mockResolvedValue(mockItems);
    mockUpdateFn.mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useCrud({
        fetchFn: mockFetchFn,
        updateFn: mockUpdateFn,
        entityName: 'test',
        onSuccess: mockOnSuccess,
      })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await result.current.update('1', updateData as any, 'Item 1');
    });

    expect(mockUpdateFn).toHaveBeenCalledWith('1', updateData);
    expect(mockToast).toHaveBeenCalledWith({
      title: 'test Updated',
      description: 'Item 1 has been updated successfully',
    });
  });

  it('should delete item successfully', async () => {
    mockFetchFn.mockResolvedValue(mockItems);
    mockDeleteFn.mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useCrud({
        fetchFn: mockFetchFn,
        deleteFn: mockDeleteFn,
        entityName: 'test',
        onSuccess: mockOnSuccess,
      })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.remove('1', 'Item 1');
    });

    expect(mockDeleteFn).toHaveBeenCalledWith('1');
    expect(mockToast).toHaveBeenCalledWith({
      title: 'test Deleted',
      description: 'Item 1 has been deleted successfully',
    });
  });
});
