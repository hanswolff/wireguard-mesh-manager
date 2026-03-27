'use client';

import { useState, useEffect } from 'react';
import { Lock, Unlock, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { LoadingButton } from '@/components/ui/loading-button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { FormErrorSummary } from '@/components/ui/form-error-summary';
import { useUnlock } from '@/contexts/unlock-context';
import { UnlockStatusDialog } from './unlock-status-dialog';
import { calculateTtlProgress } from '@/lib/utils/time-formatters';

const unlockFormSchema = z.object({
  master_password: z.string().min(1, 'Master password is required'),
  ttl_hours: z.number().min(0.1).max(24.0).optional(),
});

type UnlockFormValues = z.infer<typeof unlockFormSchema>;

interface MasterPasswordUnlockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  title?: string;
  description?: string;
}

export function MasterPasswordUnlockModal({
  isOpen,
  onClose,
  onSuccess,
  title = 'Master Password Required',
  description = 'Enter the master password to unlock sensitive operations',
}: MasterPasswordUnlockModalProps) {
  const { isUnlocked, status, unlock, extendTtl, unlockError, clearUnlockError } = useUnlock();
  const [showPassword, setShowPassword] = useState(false);
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [unlockAttempted, setUnlockAttempted] = useState(false);
  const [ttlProgress, setTtlProgress] = useState(0);

  const form = useForm<UnlockFormValues>({
    resolver: zodResolver(unlockFormSchema),
    defaultValues: {
      master_password: '',
      ttl_hours: 2,
    },
  });
  const errorMessages = Object.values(form.formState.errors)
    .map((error) => error?.message)
    .filter((message): message is string => Boolean(message));

  // Update TTL progress bar
  useEffect(() => {
    if (status?.is_unlocked && status.expires_at) {
      const updateProgress = () => {
        const progress = calculateTtlProgress(
          status.expires_at,
          status.ttl_seconds
        );
        setTtlProgress(progress);
      };

      updateProgress();
      const interval = setInterval(updateProgress, 1000);
      return () => clearInterval(interval);
    }
  }, [status]);

  const onSubmit = async (data: UnlockFormValues) => {
    setIsUnlocking(true);
    setUnlockAttempted(true);
    clearUnlockError();

    try {
      const success = await unlock(
        data.master_password,
        data.ttl_hours || undefined
      );

      if (success) {
        form.reset();
        setUnlockAttempted(false);
        onSuccess?.();
        onClose();
      }
    } finally {
      setIsUnlocking(false);
    }
  };

  const handleExtendTtl = async () => {
    const success = await extendTtl(1);
    if (success) {
      onClose();
    }
  };

  const isRouteNotFound =
    unlockError?.status === 404 ||
    Boolean(
      unlockError?.message &&
        unlockError.message.toLowerCase().includes('route_not_found')
    );

  const unlockErrorMessage =
    unlockError?.status === 401 || unlockError?.status === 403
      ? 'Invalid master password. Please try again.'
      : unlockError?.message ||
        'Unable to unlock the master password. Please try again.';

  // If already unlocked, show status dialog instead
  if (isUnlocked && status) {
    return (
      <UnlockStatusDialog
        isOpen={isOpen}
        onClose={onClose}
        status={status}
        onExtendTtl={handleExtendTtl}
        ttlProgress={ttlProgress}
      />
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormErrorSummary messages={errorMessages} />
          {/* Password Input */}
          <div className="space-y-2">
            <Label htmlFor="master_password">Master Password</Label>
            <div className="relative">
              <Input
                id="master_password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter master password"
                autoComplete="new-password"
                data-form-type="other"
                data-lpignore="true"
                {...form.register('master_password')}
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
            {form.formState.errors.master_password && (
              <p className="text-sm text-destructive">
                {form.formState.errors.master_password.message}
              </p>
            )}
          </div>

          {/* TTL Configuration */}
          <div className="space-y-2">
            <Label htmlFor="ttl_hours">Cache Duration (hours)</Label>
            <Input
              id="ttl_hours"
              type="number"
              min="0.1"
              max="24"
              step="0.1"
              placeholder="2"
              {...form.register('ttl_hours', { valueAsNumber: true })}
            />
            <p className="text-xs text-muted-foreground">
              How long to keep the master password in memory (0.1-24 hours)
            </p>
          </div>

          {/* Error Message - only show after unlock attempt completes and fails */}
          {!isUnlocking && unlockAttempted && !isUnlocked && unlockError && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                {unlockErrorMessage}
              </AlertDescription>
            </Alert>
          )}

          {isRouteNotFound && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                The backend route for master password unlock was not found.
                Check that the backend is running and the proxy is pointing to
                the correct service.
              </AlertDescription>
            </Alert>
          )}

          {/* Security Note */}
          <Alert>
            <Lock className="h-4 w-4" />
            <AlertDescription>
              The master password will be cached in memory only and
              automatically cleared after the specified duration or when you
              lock it manually.
            </AlertDescription>
          </Alert>

          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <LoadingButton
              type="submit"
              loading={isUnlocking}
              disabled={!form.formState.isValid}
              loadingText="Unlocking..."
            >
              <Unlock className="h-4 w-4 mr-2" />
              Unlock
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
