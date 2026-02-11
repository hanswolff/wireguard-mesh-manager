'use client';

import { Unlock, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  formatTimeRemaining,
} from '@/lib/utils/time-formatters';
import apiClient from '@/lib/api-client';
import { type MasterPasswordStatusResponse } from '@/lib/api-client';

interface UnlockStatusDialogProps {
  isOpen: boolean;
  onClose: () => void;
  status: MasterPasswordStatusResponse;
  onExtendTtl: () => void;
  ttlProgress: number;
}

export function UnlockStatusDialog({
  isOpen,
  onClose,
  status,
  onExtendTtl,
  ttlProgress,
}: UnlockStatusDialogProps) {
  const handleLock = async () => {
    await apiClient.lockMasterPassword();
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Unlock className="h-5 w-5 text-success" />
            Master Password Unlocked
          </DialogTitle>
          <DialogDescription>
            The master password is currently cached and available for sensitive
            operations.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Status Information */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <Label className="text-xs text-muted-foreground">Status</Label>
              <Badge
                variant="outline"
                className="mt-1 border-success-border bg-success-surface text-success-foreground"
              >
                <Unlock className="h-3 w-3 mr-1" />
                Unlocked
              </Badge>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">
                Expires In
              </Label>
              <div className="font-medium mt-1">
                {formatTimeRemaining(status.expires_at)}
              </div>
            </div>
          </div>

          {/* TTL Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Cache Duration</span>
              <span>{Math.round(ttlProgress)}%</span>
            </div>
            <Progress
              value={ttlProgress}
              className="h-2"
              indicatorClassName="bg-success"
            />
          </div>

          {/* Access Statistics */}
          <div className="text-xs text-muted-foreground">
            <div>Accessed {status.access_count} times</div>
            {status.last_access && (
              <div>
                Last access: {new Date(status.last_access).toLocaleString()}
              </div>
            )}
          </div>

          <Alert>
            <Clock className="h-4 w-4" />
            <AlertDescription>
              The master password will automatically lock when the cache
              expires. You can extend the cache duration if needed.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleLock}>
            Lock Now
          </Button>
          <Button variant="secondary" onClick={onExtendTtl}>
            Extend 1 Hour
          </Button>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
