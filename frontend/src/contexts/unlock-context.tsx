'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react';
import { toast } from '@/components/ui/use-toast';
import apiClient, {
  type MasterPasswordStatusResponse,
  type MasterPasswordUnlockRequest,
} from '@/lib/api-client';
import {
  clearMasterSessionToken,
  getMasterSessionToken,
  setMasterSessionToken,
} from '@/lib/auth';

interface ApiError extends Error {
  status?: number;
  isUnauthorized?: boolean;
}

interface UnlockError {
  message: string;
  status?: number;
  isServerError: boolean;
}

interface UnlockContextType {
  isUnlocked: boolean;
  isChecking: boolean;
  status: MasterPasswordStatusResponse | null;
  unlock: (password: string, ttlHours?: number) => Promise<boolean>;
  lock: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  extendTtl: (additionalHours: number) => Promise<boolean>;
  requireUnlock: (callback?: () => void) => boolean;
  unlockError: UnlockError | null;
  clearUnlockError: () => void;
}

const UnlockContext = createContext<UnlockContextType | undefined>(undefined);

interface UnlockProviderProps {
  children: ReactNode;
}

export function UnlockProvider({ children }: UnlockProviderProps) {
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [status, setStatus] = useState<MasterPasswordStatusResponse | null>(
    null
  );
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [lastCheck, setLastCheck] = useState<number>(0);
  const [unlockError, setUnlockError] = useState<UnlockError | null>(null);

  // Check status on mount and periodically
  useEffect(() => {
    refreshStatus();

    // Check status every 30 seconds if unlocked
    const interval = setInterval(() => {
      if (isUnlocked) {
        refreshStatus(false);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [isUnlocked]);

  const refreshStatus = async (showError = true) => {
    if (!getMasterSessionToken()) {
      // Use public endpoint when no token exists
      try {
        const unlockStatus = await apiClient.isMasterPasswordUnlocked();
        setIsUnlocked(unlockStatus.is_unlocked);
        setStatus(null);
        setIsChecking(false);
      } catch (error: unknown) {
        console.error('Failed to check master password unlock status:', error);
        setIsUnlocked(false);
        setStatus(null);
        setIsChecking(false);
      }
      return;
    }

    try {
      const currentStatus = await apiClient.getMasterPasswordStatus();
      setStatus(currentStatus);
      setIsUnlocked(currentStatus.is_unlocked);
      setLastCheck(Date.now());

      // Auto-lock if expired
      if (currentStatus.is_unlocked && currentStatus.expires_at) {
        const now = new Date();
        const expiresAt = new Date(currentStatus.expires_at);
        if (expiresAt <= now) {
          setIsUnlocked(false);
        }
      }
    } catch (error: unknown) {
      // Don't show error toast for 401 Unauthorized responses (expected when locked)
      const err = error as ApiError;
      const isUnauthorized = err?.isUnauthorized || (err?.message && err.message.includes('401'));

      if (showError && !isUnauthorized) {
        console.error('Failed to check master password status:', error);
        toast({
          title: 'Error',
          description: 'Failed to check master password status',
          variant: 'destructive',
        });
      }
      setIsUnlocked(false);
      setStatus(null);
    } finally {
      setIsChecking(false);
    }
  };

  const unlock = async (
    password: string,
    ttlHours?: number
  ): Promise<boolean> => {
    setUnlockError(null);
    try {
      const request: MasterPasswordUnlockRequest = {
        master_password: password,
        ttl_hours: ttlHours || null,
      };

      const response = await apiClient.unlockMasterPassword(request);

      if (response.success && response.session_token) {
        setMasterSessionToken(response.session_token);
        await refreshStatus();
        toast({
          title: 'Unlocked',
          description: 'Master password cached successfully',
        });
        return true;
      } else {
        const message =
          response.message || 'Failed to unlock master password';
        setUnlockError({
          message,
          isServerError: false,
        });
        toast({
          title: 'Unlock Failed',
          description: message,
          variant: 'destructive',
        });
        return false;
      }
    } catch (error) {
      const apiError = error as ApiError;
      const isServerError = (apiError.status ?? 0) >= 500;
      setUnlockError({
        message:
          error instanceof Error
            ? error.message
            : 'Failed to unlock master password',
        status: apiError.status,
        isServerError,
      });
      toast({
        title: 'Unlock Failed',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to unlock master password',
        variant: 'destructive',
      });
      return false;
    }
  };

  const lock = async (): Promise<void> => {
    try {
      await apiClient.lockMasterPassword();
      clearMasterSessionToken();
      setIsUnlocked(false);
      setStatus(null);
      toast({
        title: 'Locked',
        description: 'Master password cache cleared',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to lock master password',
        variant: 'destructive',
      });
    }
  };

  const extendTtl = async (additionalHours: number): Promise<boolean> => {
    try {
      const response = await apiClient.extendMasterPasswordTTL({
        additional_hours: additionalHours,
      });

      if (response.success) {
        await refreshStatus();
        toast({
          title: 'Extended',
          description: `Master password cache extended by ${additionalHours} hour(s)`,
        });
        return true;
      } else {
        toast({
          title: 'Extension Failed',
          description: response.message || 'Failed to extend TTL',
          variant: 'destructive',
        });
        return false;
      }
    } catch (error) {
      toast({
        title: 'Extension Failed',
        description:
          error instanceof Error ? error.message : 'Failed to extend TTL',
        variant: 'destructive',
      });
      return false;
    }
  };

  const requireUnlock = (callback?: () => void): boolean => {
    if (isChecking) {
      return false;
    }

    if (isUnlocked) {
      callback?.();
      return true;
    }

    return false;
  };

  const clearUnlockError = () => {
    setUnlockError(null);
  };

  const contextValue: UnlockContextType = {
    isUnlocked,
    isChecking,
    status,
    unlock,
    lock,
    refreshStatus: () => refreshStatus(true),
    extendTtl,
    requireUnlock,
    unlockError,
    clearUnlockError,
  };

  return (
    <UnlockContext.Provider value={contextValue}>
      {children}
    </UnlockContext.Provider>
  );
}

export function useUnlock(): UnlockContextType {
  const context = useContext(UnlockContext);
  if (context === undefined) {
    throw new Error('useUnlock must be used within an UnlockProvider');
  }
  return context;
}

// HOC to protect components that require unlock
export function withUnlock<T extends object>(
  Component: React.ComponentType<T>
) {
  return function UnlockProtectedComponent(props: T) {
    const { isUnlocked, isChecking } = useUnlock();

    if (isChecking) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      );
    }

    if (!isUnlocked) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="text-center">
            <h3 className="text-lg font-semibold mb-2">
              Master Password Required
            </h3>
            <p className="text-muted-foreground">
              This action requires the master password to be unlocked.
            </p>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };
}
