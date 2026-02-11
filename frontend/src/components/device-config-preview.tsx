'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Eye,
  EyeOff,
  Download,
  Copy,
  Shield,
  Lock,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from '@/components/ui/use-toast';
import { useUnlock } from '@/contexts/unlock-context';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import apiClient, { type DeviceResponse, type DeviceConfigResponse } from '@/lib/api-client';

type NormalizedConfigResponse = {
  device_id: string;
  device_name: string;
  network_name: string;
  configuration: string;
  format: string;
  created_at: string;
};

interface DeviceConfigPreviewProps {
  device: DeviceResponse;
}

export function DeviceConfigPreview({ device }: DeviceConfigPreviewProps) {
  const { isUnlocked, requireUnlock } = useUnlock();
  const [config, setConfig] = useState<NormalizedConfigResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [copying, setCopying] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [pendingAction, setPendingAction] = useState<
    'preview' | 'download' | null
  >(null);

  const normalizeConfig = useCallback(
    (raw: DeviceConfigResponse): NormalizedConfigResponse => {
      const configValue =
        typeof raw.configuration === 'string'
          ? raw.configuration
          : raw.configuration
            ? JSON.stringify(raw.configuration, null, 2)
            : '';

      return {
        device_id: raw.device_id,
        device_name: raw.device_name,
        network_name: raw.network_name,
        configuration: configValue,
        format: raw.format,
        created_at: raw.created_at,
      };
    },
    []
  );

  const loadConfig = useCallback(async () => {
    if (!isUnlocked) return;

    setLoading(true);
    setError(null);

    try {
      const configData = await apiClient.getAdminDeviceConfig(device.id, {
        format: 'wg',
      });
      const normalized = normalizeConfig(configData);
      setConfig(normalized);
      return normalized;
    } catch (error) {
      const errorMsg =
        error instanceof Error
          ? error.message
          : 'Failed to load device configuration';
      setError(errorMsg);
      toast({
        title: 'Error',
        description: errorMsg,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
    return null;
  }, [device.id, isUnlocked, normalizeConfig]);

  const handlePreviewConfig = useCallback(() => {
    if (showConfig) {
      setShowConfig(false);
      return;
    }

    const unlocked = requireUnlock(() => loadConfig());
    if (!unlocked) {
      setPendingAction('preview');
      setShowUnlockModal(true);
      return;
    }
    setShowConfig(true);
  }, [showConfig, requireUnlock, loadConfig]);

  const downloadConfigUnlocked = useCallback(async () => {
    try {
      await apiClient.downloadAdminDeviceConfig(device.id);
      toast({
        title: 'Configuration Downloaded',
        description: `Device configuration for ${device.name} has been downloaded securely`,
      });
    } catch (error) {
      const errorMsg =
        error instanceof Error
          ? error.message
          : 'Failed to download device configuration';
      toast({
        title: 'Error',
        description: errorMsg,
        variant: 'destructive',
      });
    }
  }, [device.id, device.name]);

  const handleDownloadConfig = useCallback(() => {
    const unlocked = requireUnlock(() => downloadConfigUnlocked());
    if (!unlocked) {
      setPendingAction('download');
      setShowUnlockModal(true);
    }
  }, [downloadConfigUnlocked, requireUnlock]);

  const handleCopyConfig = useCallback(async () => {
    if (!config) return;

    setCopying(true);
    try {
      await navigator.clipboard.writeText(config.configuration);
      toast({
        title: 'Configuration Copied',
        description: 'Device configuration has been copied to clipboard',
      });
    } catch {
      toast({
        title: 'Copy Failed',
        description: 'Failed to copy configuration to clipboard',
        variant: 'destructive',
      });
    } finally {
      setCopying(false);
    }
  }, [config]);

  const handleUnlockSuccess = useCallback(() => {
    setShowUnlockModal(false);
    const action = pendingAction;
    setPendingAction(null);
    if (action === 'download') {
      void downloadConfigUnlocked();
      return;
    }
    if (action === 'preview') {
      setShowConfig(true);
      void loadConfig();
    }
  }, [pendingAction, downloadConfigUnlocked, loadConfig]);

  useEffect(() => {
    if (isUnlocked && showConfig && !config) {
      void loadConfig();
    }
  }, [isUnlocked, showConfig, config, loadConfig]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Device Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isUnlocked && (
          <Alert>
            <Lock className="h-4 w-4" />
            <AlertDescription>
              Device configuration access requires the master password to be
              unlocked. This ensures sensitive information is protected.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handlePreviewConfig}
            disabled={loading}
            className="flex items-center gap-2"
          >
            {showConfig ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
            {showConfig ? 'Hide Config' : 'Preview Config'}
          </Button>

          <Button
            variant="outline"
            onClick={handleDownloadConfig}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Download Config
          </Button>

          {showConfig && config && (
            <>
              <Button
                variant="outline"
                onClick={handleCopyConfig}
                disabled={copying}
                className="flex items-center gap-2"
              >
                <Copy className="h-4 w-4" />
                {copying ? 'Copying...' : 'Copy Config'}
              </Button>
            </>
          )}
        </div>

        {loading && (
          <div className="flex items-center justify-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-2">Loading device configuration...</span>
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {showConfig && config && !loading && !error && (
          <div className="space-y-4">
            <Alert>
              <Shield className="h-4 w-4" />
              <AlertDescription>
                This configuration contains sensitive information. Handle with
                care and never share it unauthorized.
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <h4 className="font-medium">Configuration Details</h4>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>
                  <strong>Device:</strong> {config.device_name}
                </p>
                <p>
                  <strong>Network:</strong> {config.network_name}
                </p>
                {config.created_at && (
                  <p>
                    <strong>Created At:</strong>{' '}
                    {new Date(config.created_at).toLocaleString()}
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">Configuration Preview</h4>
              <div className="bg-muted p-4 rounded-md">
                <pre className="text-xs overflow-auto max-h-96 whitespace-pre-wrap">
                  {config.configuration}
                </pre>
              </div>
            </div>
          </div>
        )}
      </CardContent>
      {showUnlockModal && (
        <MasterPasswordUnlockModal
          isOpen={showUnlockModal}
          onClose={() => {
            setShowUnlockModal(false);
            setPendingAction(null);
          }}
          onSuccess={handleUnlockSuccess}
          title="Unlock to Access Configuration"
          description="Enter the master password to access device configurations."
        />
      )}
    </Card>
  );
}
