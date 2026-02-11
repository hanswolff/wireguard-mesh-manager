'use client';

import { useState, useCallback } from 'react';
import { toast } from '@/components/ui/use-toast';
import { useUnlock } from '@/contexts/unlock-context';

interface UseMasterPasswordOptions {
  onSuccess?: () => void;
  onFailure?: () => void;
  customMessage?: string;
}

export function useMasterPassword(options: UseMasterPasswordOptions = {}) {
  const { isUnlocked, isChecking } = useUnlock();
  const [showUnlockModal, setShowUnlockModal] = useState(false);

  const requireUnlock = useCallback(
    (callback?: () => void) => {
      // If checking status, wait
      if (isChecking) {
        return false;
      }

      // If already unlocked, execute callback
      if (isUnlocked) {
        callback?.();
        options.onSuccess?.();
        return true;
      }

      // Show unlock modal
      setShowUnlockModal(true);
      return false;
    },
    [isUnlocked, isChecking, options]
  );

  const handleUnlockSuccess = useCallback(() => {
    setShowUnlockModal(false);
    options.onSuccess?.();
  }, [options]);

  const handleUnlockFailure = useCallback(() => {
    setShowUnlockModal(false);
    options.onFailure?.();

    if (options.customMessage) {
      toast({
        title: 'Authentication Required',
        description: options.customMessage,
        variant: 'destructive',
      });
    }
  }, [options]);

  const ensureUnlocked = useCallback((): Promise<boolean> => {
    return new Promise((resolve) => {
      if (isChecking) {
        // Poll until checking is complete
        const checkInterval = setInterval(() => {
          if (!isChecking) {
            clearInterval(checkInterval);
            resolve(requireUnlock());
          }
        }, 100);
        return;
      }

      if (isUnlocked) {
        resolve(true);
      } else {
        setShowUnlockModal(true);
        // Set up a one-time listener for successful unlock
        const originalOnSuccess = options.onSuccess;
        options.onSuccess = () => {
          originalOnSuccess?.();
          resolve(true);
        };
      }
    });
  }, [isUnlocked, isChecking, requireUnlock, options]);

  return {
    requireUnlock,
    ensureUnlocked,
    showUnlockModal,
    setShowUnlockModal,
    handleUnlockSuccess,
    handleUnlockFailure,
    isUnlocked,
    isChecking,
  };
}
