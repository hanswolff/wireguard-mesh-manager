'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Cpu,
  Edit,
  Download,
  Shield,
  Key,
  Globe,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/components/ui/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient, { type DeviceResponse } from '@/lib/api-client';
import Link from 'next/link';
import { DeviceDetailSkeleton } from './loading-skeleton';
import { OverviewTab } from './overview-tab';
import { ApiManagementTab } from './api-management-tab';
import { NetworkConfigTab } from './network-config-tab';
import { StatusCards } from './status-cards';
import { DeviceConfigPreview } from '@/components/device-config-preview';
import { useBreadcrumbs } from '@/components/breadcrumb-provider';

export default function DeviceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [device, setDevice] = useState<DeviceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string>('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [regeneratingKey, setRegeneratingKey] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const { setLabel } = useBreadcrumbs();

  useEffect(() => {
    // Load saved tab from localStorage
    const savedTab = localStorage.getItem(`device-tab-${params.deviceId}`);
    if (savedTab === 'overview' || savedTab === 'api' || savedTab === 'network' || savedTab === 'config') {
      setActiveTab(savedTab);
    }
  }, [params.deviceId]);

  useEffect(() => {
    // Save active tab to localStorage
    if (params.deviceId) {
      localStorage.setItem(`device-tab-${params.deviceId}`, activeTab);
    }
  }, [activeTab, params.deviceId]);

  useEffect(() => {
    if (params.deviceId) {
      fetchDevice(params.deviceId as string);
    }
  }, [params.deviceId]);

  const fetchDevice = async (deviceId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getDevice(deviceId);
      setDevice(data);
      // Set breadcrumb label for the device
      setLabel(`/networks/${data.network_id}/devices/${deviceId}`, data.name || deviceId);
      // Set breadcrumb label for the network if available
      if (data.network_name) {
        setLabel(`/networks/${data.network_id}`, data.network_name);
      }
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : 'Failed to fetch device details'
      );
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to fetch device details',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateApiKey = async () => {
    if (!device) return;

    try {
      setRegeneratingKey(true);
      const response = await apiClient.regenerateDeviceApiKey(device.id);
      setApiKey(response.api_key);
      setShowApiKey(true);
      toast({
        title: 'API Key Regenerated',
        description:
          'New API key has been generated. Please save it securely as it will only be shown once.',
      });
      await fetchDevice(device.id);
    } catch (error) {
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to regenerate API key',
        variant: 'destructive',
      });
    } finally {
      setRegeneratingKey(false);
    }
  };

  const downloadConfig = async () => {
    if (!device) return;

    try {
      await apiClient.downloadAdminDeviceConfig(device.id);

      toast({
        title: 'Configuration Downloaded',
        description: `Device configuration for ${device.name} has been downloaded`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to download configuration',
        variant: 'destructive',
      });
    }
  };

  if (loading) {
    return <DeviceDetailSkeleton />;
  }

  if (error || !device) {
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
          <AlertDescription>{error || 'Device not found'}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DeviceHeader device={device} onDownloadConfig={downloadConfig} />
      <StatusCards device={device} />
      <DeviceDetailsTabs
        device={device}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onRegenerateApiKey={handleRegenerateApiKey}
        isRegeneratingKey={regeneratingKey}
        apiKey={apiKey}
        showApiKey={showApiKey}
        onApiKeyGenerated={setApiKey}
        onDownloadConfig={downloadConfig}
      />
    </div>
  );
}

function DeviceHeader({
  device,
  onDownloadConfig,
}: {
  device: DeviceResponse;
  onDownloadConfig: () => void;
}) {
  const router = useRouter();

  const handleBackToDevices = () => {
    // Set the devices tab as active in localStorage
    try {
      localStorage.setItem(`network-tab-${device.network_id}`, 'devices');
    } catch {
      // Silently fail if localStorage is unavailable (e.g., private browsing mode)
    }
    // Navigate to the network page
    router.push(`/networks/${device.network_id}`);
  };

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <Button variant="ghost" onClick={handleBackToDevices}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Devices
        </Button>
        <div className="flex items-center space-x-3">
          <Cpu className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              {device.name}
              <Badge variant={device.enabled ? 'default' : 'secondary'}>
                {device.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </h1>
            <p className="text-muted-foreground">
              {device.description || 'No description provided'}
            </p>
          </div>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        <Link href={`/networks/${device.network_id}/devices/${device.id}/edit`}>
          <Button variant="outline">
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
        </Link>
        <Button variant="outline" onClick={onDownloadConfig}>
          <Download className="h-4 w-4 mr-2" />
          Download Config
        </Button>
      </div>
    </div>
  );
}

function DeviceDetailsTabs({
  device,
  activeTab,
  onTabChange,
  onRegenerateApiKey,
  isRegeneratingKey,
  apiKey,
  showApiKey,
  onApiKeyGenerated,
  onDownloadConfig,
}: {
  device: DeviceResponse;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onRegenerateApiKey: () => Promise<void>;
  isRegeneratingKey: boolean;
  apiKey: string;
  showApiKey: boolean;
  onApiKeyGenerated: (apiKey: string) => void;
  onDownloadConfig: () => void;
}) {
  return (
    <Tabs value={activeTab} onValueChange={onTabChange} className="space-y-4">
      <TabsList>
        <TabsTrigger value="overview">
          <Shield className="h-4 w-4 mr-2" />
          Overview
        </TabsTrigger>
        <TabsTrigger value="api">
          <Key className="h-4 w-4 mr-2" />
          API Management
        </TabsTrigger>
        <TabsTrigger value="network">
          <Globe className="h-4 w-4 mr-2" />
          Network Config
        </TabsTrigger>
        <TabsTrigger value="config">
          <Download className="h-4 w-4 mr-2" />
          Config Preview
        </TabsTrigger>
      </TabsList>

      <TabsContent value="overview">
        <OverviewTab device={device} />
      </TabsContent>

      <TabsContent value="api">
        <ApiManagementTab
          device={device}
          onRegenerateApiKey={onRegenerateApiKey}
          isRegeneratingKey={isRegeneratingKey}
          newApiKey={apiKey}
          showNewApiKey={showApiKey}
          onApiKeyGenerated={onApiKeyGenerated}
        />
      </TabsContent>

      <TabsContent value="network">
        <NetworkConfigTab device={device} onDownloadConfig={onDownloadConfig} />
      </TabsContent>

      <TabsContent value="config">
        <DeviceConfigPreview device={device} />
      </TabsContent>
    </Tabs>
  );
}
