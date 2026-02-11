'use client';

import { Lock, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import { useUnlock } from '@/contexts/unlock-context';
import { useState } from 'react';

interface LockedPlaceholderProps {
  children: React.ReactNode;
}

export function LockedPlaceholder({ children }: LockedPlaceholderProps) {
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const { isUnlocked } = useUnlock();

  const handleUnlockSuccess = () => {
    setShowUnlockModal(false);
    // The page will automatically re-render due to unlock context update
  };

  // If unlocked, render children
  if (isUnlocked) {
    return <>{children}</>;
  }

  return (
    <div className="flex items-center justify-center h-full">
      <Card className="max-w-md w-full mx-4">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Lock className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">Master Password Required</CardTitle>
          <CardDescription>
            Unlock the application to access WireGuard cluster management and
            configuration features.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2 rounded-lg bg-muted/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Shield className="h-4 w-4 text-primary" />
              <span>Secure Access</span>
            </div>
            <p className="text-xs text-muted-foreground">
              The master password is required to decrypt private keys, manage
              devices, and export sensitive configuration data.
            </p>
          </div>

          <Button
            onClick={() => setShowUnlockModal(true)}
            className="w-full"
            size="lg"
          >
            <Lock className="h-4 w-4 mr-2" />
            Unlock with Master Password
          </Button>
        </CardContent>
      </Card>

      <MasterPasswordUnlockModal
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
        onSuccess={handleUnlockSuccess}
        title="Unlock WireGuard Mesh Manager"
        description="Enter the master password to access the cluster management interface."
      />
    </div>
  );
}
