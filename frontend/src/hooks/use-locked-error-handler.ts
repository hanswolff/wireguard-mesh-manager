'use client';

import { useCallback } from 'react';
import { toast } from '@/components/ui/use-toast';
import { useUnlock } from '@/contexts/unlock-context';
import {
  isLockedError,
  getErrorMessage,
  getErrorTitle,
} from '@/lib/error-handler';

/**
 * Hook to handle locked (423) errors consistently across the application.
 *
 * When a 423 error is received, this hook will:
 * 1. Force the unlock context to locked state
 * 2. Show an appropriate toast message
 * 3. Optionally trigger the unlock modal
 *
 * Usage:
 * ```tsx
 * const { handleLockedError, handleLockedErrorWithUnlock } = useLockedErrorHandler();
 *
 * try {
 *   await apiClient.updateDevice(...);
 * } catch (error) {
 *   if (handleLockedErrorWithUnlock(error)) {
 *     return; // Error was handled, unlock modal triggered
 *   }
 *   // Handle other errors
 * }
 * ```
 */
export function useLockedErrorHandler() {
  const { forceLock, showUnlockModal } = useUnlock();

  const handleLockedError = useCallback(
    (error: unknown): boolean => {
      if (!isLockedError(error)) {
        return false;
      }

      // Force the unlock context to locked state
      forceLock();

      // Show a toast with appropriate message
      toast({
        title: getErrorTitle(error),
        description: getErrorMessage(error),
        variant: 'destructive',
      });

      return true;
    },
    [forceLock]
  );

  const handleLockedErrorWithUnlock = useCallback(
    (error: unknown): boolean => {
      if (!isLockedError(error)) {
        return false;
      }

      // Force the unlock context to locked state
      forceLock();

      // Show a toast with appropriate message
      toast({
        title: getErrorTitle(error),
        description: getErrorMessage(error),
        variant: 'destructive',
      });

      // Trigger the unlock modal
      showUnlockModal();

      return true;
    },
    [forceLock, showUnlockModal]
  );

  return {
    handleLockedError,
    handleLockedErrorWithUnlock,
    isLockedError,
  };
}
