'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Download, Shield, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import { useUnlock } from '@/contexts/unlock-context';
import { toast } from '@/components/ui/use-toast';
import apiClient, { type WireGuardNetworkResponse } from '@/lib/api-client';
import {
  downloadFile,
  generateExportFilename,
  type ExportFormat,
} from '@/lib/export-utils';
import { NetworkOverviewCard } from '@/components/networks/network-overview-card';
import { ExportFormatCard } from '@/components/networks/export-format-card';
import { ExportOptionsCard } from '@/components/networks/export-options-card';
import { ExportActionCard } from '@/components/networks/export-action-card';
import { useBreadcrumbs } from '@/components/breadcrumb-provider';

export default function NetworkExportPage() {
  const params = useParams();
  const router = useRouter();
  const [network, setNetwork] = useState<WireGuardNetworkResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'wg' | 'json' | 'mobile'>(
    'wg'
  );
  const [includePresharedKeys, setIncludePresharedKeys] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);

  const { isUnlocked, requireUnlock } = useUnlock();
  const { setLabel } = useBreadcrumbs();

  useEffect(() => {
    if (params.id) {
      fetchNetwork(params.id as string);
    }
  }, [params.id]);

  const fetchNetwork = async (networkId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getNetwork(networkId);
      setNetwork(data);
      setLabel(`/networks/${networkId}`, data.name || networkId);
      setLabel(`/networks/${networkId}/export`, 'Export');
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Failed to fetch network details';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    // All config exports require master password for private key decryption
    const canProceed = requireUnlock(executeExport);
    if (!canProceed) {
      setShowUnlockModal(true);
      return;
    }
  };

  const executeExport = async () => {
    if (!network) return;

    setIsExporting(true);
    try {
      const blob = await apiClient.downloadNetworkConfigs(network.id, {
        format: exportFormat,
        includePresharedKeys: includePresharedKeys,
      });

      const filename = generateExportFilename(network.name, exportFormat);
      downloadFile(blob, filename);

      toast({
        title: 'Export Successful',
        description: `${network.name} device configurations exported successfully in ${exportFormat.toUpperCase()} format`,
      });
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Failed to export network configurations';
      toast({
        title: 'Export Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleUnlockSuccess = () => {
    setShowUnlockModal(false);
    executeExport();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <Skeleton className="h-8 w-[200px]" />
            <Skeleton className="h-4 w-[300px]" />
          </div>
        </div>
        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-[150px]" />
            </CardHeader>
            <CardContent className="space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (error || !network) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error || 'Network not found'}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Button variant="ghost" onClick={() => router.push(`/networks/${network.id}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Network
        </Button>
        <div className="flex items-center space-x-3">
          <Download className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Export Network Configs</h1>
            <p className="text-muted-foreground">
              Export device configurations for <strong>{network.name}</strong>
            </p>
          </div>
        </div>
      </div>

      {/* Network Overview */}
      <NetworkOverviewCard network={network} />

      {/* Export Status */}
      {isUnlocked ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-success" />
              Master Password Unlocked
            </CardTitle>
            <CardDescription>
              Private keys can be exported as the master password is currently
              unlocked
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="secondary">
              <Shield className="h-3 w-3 mr-1" />
              Ready for export
            </Badge>
          </CardContent>
        </Card>
      ) : (
        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            <strong>Master Password Required:</strong> Exporting device
            configurations requires the master password to decrypt private keys.
          </AlertDescription>
        </Alert>
      )}

      {/* Export Format Options */}
      <ExportFormatCard
        value={exportFormat}
        onValueChange={(value) => setExportFormat(value as ExportFormat)}
      />

      {/* Additional Options */}
      <ExportOptionsCard
        includePresharedKeys={includePresharedKeys}
        onIncludePresharedKeysChange={setIncludePresharedKeys}
        exportFormat={exportFormat}
      />

      {/* Security Warning */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <strong>Security Notice:</strong> This export contains sensitive data
          including private keys for all devices in the network. Ensure the ZIP
          file is stored securely and shared only with authorized personnel.
        </AlertDescription>
      </Alert>

      {/* Export Action */}
      <ExportActionCard
        networkName={network.name}
        deviceCount={network.device_count}
        exportFormat={exportFormat}
        includePresharedKeys={includePresharedKeys}
        isExporting={isExporting}
        onExport={handleExport}
      />

      {/* Unlock Modal */}
      <MasterPasswordUnlockModal
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
        onSuccess={handleUnlockSuccess}
        title="Master Password Required for Export"
        description="Enter the master password to decrypt and export private keys for all devices in this network."
      />
    </div>
  );
}
