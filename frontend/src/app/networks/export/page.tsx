'use client';

import { useState } from 'react';
import { Download, Shield, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LoadingButton } from '@/components/ui/loading-button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import { useUnlock } from '@/contexts/unlock-context';
import { toast } from '@/components/ui/use-toast';
import apiClient, { type ExportRequest } from '@/lib/api-client';

export default function NetworksExportPage() {
  const [isExporting, setIsExporting] = useState(false);
  const [includeConfigs, setIncludeConfigs] = useState(true);
  const [includeApiKeys, setIncludeApiKeys] = useState(false);
  const [exportFormat, setExportFormat] = useState<'json' | 'zip'>('json');
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [selectedNetworks, setSelectedNetworks] = useState<string[]>([]);

  const { isUnlocked, requireUnlock } = useUnlock();

  const handleExport = async () => {
    // Configs include private keys, so require unlock for that
    if (includeConfigs) {
      const canProceed = requireUnlock(executeExport);
      if (!canProceed) {
        setShowUnlockModal(true);
        return;
      }
    } else {
      executeExport();
    }
  };

  const executeExport = async () => {
    setIsExporting(true);
    try {
      const exportData: ExportRequest = {
        network_ids: selectedNetworks.length > 0 ? selectedNetworks : undefined,
        include_configs: includeConfigs,
        include_api_keys: includeApiKeys,
        format: exportFormat,
      };

      if (exportFormat === 'json') {
        // Direct JSON download
        const result = await apiClient.exportNetworks(exportData);

        // Create and download JSON file
        const blob = new Blob([JSON.stringify(result, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `networks-export-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        // ZIP download
        const blob = await apiClient.downloadExport(exportData);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `networks-export-${new Date().toISOString().split('T')[0]}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }

      toast({
        title: 'Export Successful',
        description: `Networks exported successfully in ${exportFormat.toUpperCase()} format`,
      });

      // Reset form
      setSelectedNetworks([]);
    } catch (error) {
      toast({
        title: 'Export Failed',
        description:
          error instanceof Error ? error.message : 'Failed to export networks',
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

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3">
        <Download className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Export Networks</h1>
          <p className="text-muted-foreground">
            Export network configurations with optional private keys and device
            data
          </p>
        </div>
      </div>

      {/* Export Status */}
      {isUnlocked && (
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
      )}

      {/* Export Options */}
      <Card>
        <CardHeader>
          <CardTitle>Export Options</CardTitle>
          <CardDescription>
            Configure what to include in the export and the output format
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Export Format */}
          <div className="space-y-2">
            <Label>Export Format</Label>
            <div className="flex gap-4">
              {(['json', 'zip'] as const).map((format) => (
                <div key={format} className="flex items-center space-x-2">
                  <Checkbox
                    id={`format-${format}`}
                    checked={exportFormat === format}
                    onCheckedChange={() => setExportFormat(format)}
                  />
                  <Label
                    htmlFor={`format-${format}`}
                    className="text-sm font-normal"
                  >
                    {format.toUpperCase()}{' '}
                    {format === 'zip' && '(includes config files)'}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Content Options */}
          <div className="space-y-3">
            <Label>Export Content</Label>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="include-configs"
                  checked={includeConfigs}
                  onCheckedChange={(checked) =>
                    setIncludeConfigs(checked as boolean)
                  }
                />
                <div className="grid gap-1.5 leading-none">
                  <Label
                    htmlFor="include-configs"
                    className="text-sm font-normal"
                  >
                    Include Network Configurations
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Export network configurations and private keys (requires
                    master password)
                  </p>
                </div>
                {includeConfigs && !isUnlocked && (
                  <Badge variant="outline" className="ml-2">
                    <Shield className="h-3 w-3 mr-1" />
                    Unlock Required
                  </Badge>
                )}
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="include-api-keys"
                  checked={includeApiKeys}
                  onCheckedChange={(checked) =>
                    setIncludeApiKeys(checked as boolean)
                  }
                />
                <div className="grid gap-1.5 leading-none">
                  <Label
                    htmlFor="include-api-keys"
                    className="text-sm font-normal"
                  >
                    Include Device API Keys
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Export device API keys for configuration retrieval
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Separator />
        </CardContent>
      </Card>

      {/* Security Warning */}
      {includeConfigs && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>Security Notice:</strong> You are exporting sensitive data
            including network configurations and private keys. Ensure the export
            file is stored securely and shared only with authorized personnel.
            The exported file will contain all information needed to recreate
            the networks.
          </AlertDescription>
        </Alert>
      )}

      {/* Export Action */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Ready to Export</h3>
              <p className="text-sm text-muted-foreground">
                Export will include networks
                {includeConfigs && ' with configurations'}
                {includeApiKeys && ' and API keys'} in{' '}
                {exportFormat.toUpperCase()} format
              </p>
            </div>
            <LoadingButton
              onClick={handleExport}
              loading={isExporting}
              loadingText="Exporting..."
              size="lg"
            >
              <Download className="h-4 w-4 mr-2" />
              Export Networks
            </LoadingButton>
          </div>
        </CardContent>
      </Card>

      {/* Unlock Modal */}
      <MasterPasswordUnlockModal
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
        onSuccess={handleUnlockSuccess}
        title="Master Password Required for Export"
        description="Enter the master password to unlock private key export capabilities. This is required to decrypt and include private keys in the export."
      />
    </div>
  );
}
