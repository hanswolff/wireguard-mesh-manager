'use client';

import { Lock, Unlock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TimerBadge } from '@/components/ui/timer-badge';
import { useUnlock } from '@/contexts/unlock-context';

interface UnlockStatusButtonProps {
  onShowUnlockModal: () => void;
}

export function UnlockStatusButton({
  onShowUnlockModal,
}: UnlockStatusButtonProps) {
  const { isUnlocked, isChecking, status, lock } = useUnlock();

  if (isChecking) {
    return null;
  }

  if (isUnlocked) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="h-8 text-xs"
        onClick={lock}
      >
        <Unlock className="h-3 w-3 mr-1 text-success" />
        Unlocked
        {status?.expires_at && <TimerBadge expiresAt={status.expires_at} />}
      </Button>
    );
  }

  return (
    <Button
      variant="outline"
      size="sm"
      className="h-8 text-xs"
      onClick={onShowUnlockModal}
    >
      <Lock className="h-3 w-3 mr-1 text-muted-foreground" />
      Locked
    </Button>
  );
}
