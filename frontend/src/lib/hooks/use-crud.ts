import { useState, useCallback, useEffect } from 'react';
import { toast } from '@/components/ui/use-toast';

interface CrudOptions<T, CreateData, UpdateData> {
  fetchFn: () => Promise<T[]>;
  createFn?: (data: CreateData) => Promise<void>;
  updateFn?: (id: string, data: UpdateData) => Promise<void>;
  deleteFn?: (id: string) => Promise<void>;
  onSuccess?: (action: 'create' | 'update' | 'delete', item?: T) => void;
  entityName: string;
}

interface CrudState<T> {
  items: T[];
  loading: boolean;
  isSubmitting: boolean;
}

export function useCrud<
  T extends { id: string; name: string },
  CreateData,
  UpdateData,
>({
  fetchFn,
  createFn,
  updateFn,
  deleteFn,
  onSuccess,
  entityName,
}: CrudOptions<T, CreateData, UpdateData>) {
  const [state, setState] = useState<CrudState<T>>({
    items: [],
    loading: true,
    isSubmitting: false,
  });

  const fetch = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, loading: true }));
      const data = await fetchFn();
      setState((prev) => ({ ...prev, items: data, loading: false }));
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : `An error occurred while loading ${entityName}s`;
      toast({
        title: `Failed to fetch ${entityName}s`,
        description: errorMessage,
        variant: 'destructive',
      });
      setState((prev) => ({ ...prev, loading: false }));
    }
  }, [fetchFn, entityName]);

  // Auto-fetch on mount
  useEffect(() => {
    fetch();
  }, [fetch]);

  const create = useCallback(
    async (data: CreateData) => {
      if (!createFn) return;

      try {
        setState((prev) => ({ ...prev, isSubmitting: true }));
        await createFn(data);

        const itemName =
          data && typeof data === 'object' && 'name' in data
            ? String((data as { name?: string }).name ?? '')
            : '';
        toast({
          title: `${entityName} Created`,
          description: `${itemName} has been created successfully`,
        });

        await fetch();
        onSuccess?.('create');
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : `Failed to create ${entityName}`;
        toast({
          title: 'Create Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setState((prev) => ({ ...prev, isSubmitting: false }));
      }
    },
    [createFn, fetch, onSuccess, entityName]
  );

  const update = useCallback(
    async (id: string, data: UpdateData, itemName: string) => {
      if (!updateFn) return;

      try {
        setState((prev) => ({ ...prev, isSubmitting: true }));
        await updateFn(id, data);

        toast({
          title: `${entityName} Updated`,
          description: `${itemName} has been updated successfully`,
        });

        await fetch();
        onSuccess?.(
          'update',
          state.items.find((item) => item.id === id)
        );
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : `Failed to update ${entityName}`;
        toast({
          title: 'Update Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setState((prev) => ({ ...prev, isSubmitting: false }));
      }
    },
    [updateFn, fetch, onSuccess, entityName, state.items]
  );

  const remove = useCallback(
    async (id: string, itemName: string) => {
      if (!deleteFn) return;

      try {
        setState((prev) => ({ ...prev, isSubmitting: true }));
        await deleteFn(id);

        toast({
          title: `${entityName} Deleted`,
          description: `${itemName} has been deleted successfully`,
        });

        await fetch();
        onSuccess?.(
          'delete',
          state.items.find((item) => item.id === id)
        );
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : `Failed to delete ${entityName}`;
        toast({
          title: 'Delete Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setState((prev) => ({ ...prev, isSubmitting: false }));
      }
    },
    [deleteFn, fetch, onSuccess, entityName, state.items]
  );

  return {
    ...state,
    fetch,
    create,
    update,
    remove,
  };
}
