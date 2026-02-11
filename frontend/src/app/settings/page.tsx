'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, OperationalSettingsResponse } from '@/lib/api-client';
import { mockOperationalSettings } from '@/lib/operational-settings';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { GlobalStateWrapper } from '@/components/global-states';
import { Info, Lock } from 'lucide-react';
import { SecurityConfigurationCard } from '@/components/settings/security-configuration-card';
import { CorsConfigurationCard } from '@/components/settings/cors-configuration-card';
import { AuditConfigurationCard } from '@/components/settings/audit-configuration-card';
import { MasterPasswordCacheCard } from '@/components/settings/master-password-cache-card';
import { SettingsLoadingSkeleton } from '@/components/settings/settings-loading-skeleton';
import { getErrorMessage, isUnauthorizedError } from '@/lib/error-handler';
import { useUnlock } from '@/contexts/unlock-context';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';

export default function SettingsPage() {
  const [operationalSettings, setOperationalSettings] = useState<OperationalSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const { isUnlocked } = useUnlock();

  const refreshSettings = useCallback(async () => {
    try {
      const data = await apiClient.getOperationalSettings();
      setOperationalSettings(data);
    } catch (err) {
      const errorMessage = getErrorMessage(err, 'operational settings');
      setError(errorMessage);
    }
  }, []);

  useEffect(() => {
    refreshSettings();
  }, [refreshSettings]);

  const content = (
    <div className="space-y-6">
      {error && (
        <Alert
          variant={isUnauthorizedError(error) ? 'default' : 'destructive'}
          className={isUnauthorizedError(error) ? 'border-primary' : ''}
        >
          {isUnauthorizedError(error) && <Lock className="h-4 w-4" />}
          <AlertDescription className="ml-2">
            {error}
            {isUnauthorizedError(error) && !isUnlocked && (
              <Button
                variant="link"
                className="ml-2 p-0 h-auto"
                onClick={() => setShowUnlockModal(true)}
              >
                Unlock Now
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      {operationalSettings && (
        <>
          <SecurityConfigurationCard
            settings={operationalSettings}
            onSave={refreshSettings}
          />
          <CorsConfigurationCard settings={mockOperationalSettings} />
          <AuditConfigurationCard settings={mockOperationalSettings} />
          <MasterPasswordCacheCard settings={mockOperationalSettings} />
        </>
      )}

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Some operational settings are configured at the server level and
          require backend changes to modify. Security Configuration settings
          can be edited dynamically.
        </AlertDescription>
      </Alert>
    <MasterPasswordUnlockModal isOpen={showUnlockModal} onClose={() => setShowUnlockModal(false)} />

    </div>
  );

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          View and monitor operational configuration flags and system settings.
        </p>
      </div>

      <GlobalStateWrapper
        loading={loading && !operationalSettings}
        loadingMessage="Loading system settings..."
        error={error}
        empty={false}
        errorAction={
          <Button
            onClick={() => {
              setError(null);
              refreshSettings();
            }}
          >
            Try Again
          </Button>
        }
      >
        {loading && !operationalSettings ? <SettingsLoadingSkeleton /> : content}
      </GlobalStateWrapper>
    <MasterPasswordUnlockModal isOpen={showUnlockModal} onClose={() => setShowUnlockModal(false)} />

    </div>
  );
}
