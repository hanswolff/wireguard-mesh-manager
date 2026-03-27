'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  AlertTriangle,
  Cpu,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  type DeviceResponse,
  type DeviceUpdate,
  type LocationResponse,
  type WireGuardNetworkResponse,
} from '@/lib/api-client';
import apiClient from '@/lib/api-client';
import DeviceForm from '../../../components/device-form';
import { useBreadcrumbs } from '@/components/breadcrumb-provider';
import { getErrorMessage, getErrorTitle, isLockedError } from '@/lib/error-handler';

export default function DeviceEditPage() {
  const params = useParams();
  const router = useRouter();
  const [device, setDevice] = useState<DeviceResponse | null>(null);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [network, setNetwork] = useState<WireGuardNetworkResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { setLabel } = useBreadcrumbs();

  const networkId = params.id as string;
  const deviceId = params.deviceId as string;

  useEffect(() => {
    void fetchData();
  }, [deviceId, networkId]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [deviceData, locationsData, networkData] = await Promise.all([
        apiClient.getDevice(deviceId),
        apiClient.listLocations({ network_id: networkId }),
        apiClient.getNetwork(networkId),
      ]);

      setDevice(deviceData);
      setLocations(locationsData);
      setNetwork(networkData);

      // Set breadcrumb labels
      setLabel(`/networks/${networkId}`, networkData.name || networkId);
      setLabel(`/networks/${networkId}/devices/${deviceId}`, deviceData.name || deviceId);
    } catch (err) {
      const errorMessage = getErrorMessage(err, 'fetch device data');
      setError(errorMessage);
      toast({
        title: getErrorTitle(err),
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [deviceId, networkId, setLabel]);

  const handleSubmit = async (data: DeviceUpdate) => {
    try {
      setIsSubmitting(true);
      await apiClient.updateDevice(deviceId, data);

      toast({
        title: 'Device Updated',
        description: `${data.name} has been updated successfully`,
      });

      router.push(`/networks/${networkId}/devices/${deviceId}`);
    } catch (err) {
      const errorMessage = getErrorMessage(err, 'update device');
      toast({
        title: getErrorTitle(err),
        description: errorMessage,
        variant: 'destructive',
      });
      // Re-throw to let DeviceForm handle fieldErrors
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <div className="h-8 w-24 animate-pulse bg-muted rounded" />
          </div>
          <div className="h-64 animate-pulse bg-muted rounded-lg" />
        </div>
      </div>
    );
  }

  if (error || !device) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
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
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" onClick={() => router.push(`/networks/${networkId}/devices/${deviceId}`)}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Device
            </Button>
            <div className="flex items-center space-x-3">
              <Cpu className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-3xl font-bold">Edit Device</h1>
                <p className="text-muted-foreground">
                  {device.name}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="rounded-lg border bg-card p-6">
          <DeviceForm
            open={true}
            onOpenChange={(open) => {
              if (!open) {
                router.push(`/networks/${networkId}/devices/${deviceId}`);
              }
            }}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            device={device}
            locations={locations}
            networkId={networkId}
            networkCidr={network?.network_cidr}
            mode="edit"
          />
        </div>
      </div>
    </div>
  );
}
