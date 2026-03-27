'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { flushSync } from 'react-dom';
import { Plus, Cpu, Shield, RefreshCw, AlertTriangle } from 'lucide-react';

// Simple debounce hook that returns both the debounced function and a cancel method
function useDebounce<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): { fn: T; cancel: () => void } {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const callbackRef = useRef(callback);

  // Keep callback ref updated
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    },
    [delay]
  );

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return { fn: debouncedCallback as T, cancel };
}
import { Button } from '@/components/ui/button';
import { LoadingButton } from '@/components/ui/loading-button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import apiClient, {
  type DeviceResponse,
  type DeviceCreate,
  type DeviceUpdate,
  type DeviceKeysRegenerateResponse,
  type LocationResponse,
  type WireGuardNetworkResponse,
} from '@/lib/api-client';
import { getErrorMessage, getErrorTitle, isLockedError } from '@/lib/error-handler';
import { useLockedErrorHandler } from '@/hooks/use-locked-error-handler';

import DeviceForm from './device-form';
import DeviceFilters, {
  type SortField,
  type SortDirection,
  type EnabledFilter,
} from './device-filters';
import DevicesTable from './devices-table';

interface NetworkDevicesProps {
  networkId: string;
  onDeviceChanged?: () => void;
}

export default function NetworkDevices({ networkId, onDeviceChanged }: NetworkDevicesProps) {
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [network, setNetwork] = useState<WireGuardNetworkResponse | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showApiKeyDialog, setShowApiKeyDialog] = useState(false);
  const [showRegenerateKeysDialog, setShowRegenerateKeysDialog] = useState(false);

  // Selected device for operations
  const [selectedDevice, setSelectedDevice] = useState<DeviceResponse | null>(
    null
  );
  const [newApiKey, setNewApiKey] = useState<string>('');
  const [regeneratedKeys, setRegeneratedKeys] = useState<DeviceKeysRegenerateResponse | null>(null);

  // Filtering and sorting state
  const [searchQuery, setSearchQuery] = useState('');
  const [locationFilter, setLocationFilter] = useState<string>('all');
  const [enabledFilter, setEnabledFilter] = useState<EnabledFilter>('all');
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [showFilters, setShowFilters] = useState(false);

  // Debounced fetch function to avoid API calls on every keystroke
  // Returns object with { fn, cancel } for managing debounce lifecycle
  const debouncedFetch = useDebounce(() => {
    fetchDevices();
  }, 300);

  useEffect(() => {
    fetchDevices(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [networkId]);

  useEffect(() => {
    if (initialLoading) {
      // Don't debounce the initial load
      return;
    }
    debouncedFetch.fn();

    // Cleanup: cancel any pending debounce when filters change
    return () => {
      debouncedFetch.cancel();
    };
  }, [
    searchQuery,
    locationFilter,
    enabledFilter,
  ]);

  useEffect(() => {
    fetchLocations();
    fetchNetwork();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [networkId]);

  const fetchNetwork = useCallback(async () => {
    try {
      const data = await apiClient.getNetwork(networkId);
      setNetwork(data);
    } catch (error: unknown) {
      console.error('Failed to fetch network:', error);
    }
  }, [networkId]);

  const fetchDevices = useCallback(async (isInitialLoad = false) => {
    try {
      if (isInitialLoad) {
        setInitialLoading(true);
      } else {
        setFetching(true);
      }
      setFetchError(null);
      const params = {
        network_id: networkId,
        ...(searchQuery && { search: searchQuery }),
        ...(locationFilter !== 'all' && { location_id: locationFilter }),
        ...(enabledFilter !== 'all' && { enabled: enabledFilter === 'true' }),
      };

      const data = await apiClient.listDevices(params);
      setDevices(data);
      setFetchError(null);
    } catch (error: unknown) {
      const errorMessage = getErrorMessage(error, 'load devices');
      setFetchError(errorMessage);
      toast({
        title: getErrorTitle(error),
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      if (isInitialLoad) {
        setInitialLoading(false);
      } else {
        setFetching(false);
      }
    }
  }, [networkId, searchQuery, locationFilter, enabledFilter]);

  const fetchLocations = useCallback(async () => {
    try {
      const data = await apiClient.listLocations({ network_id: networkId });
      setLocations(data);
    } catch (error: unknown) {
      console.error('Failed to fetch locations:', error);
    }
  }, [networkId]);

  const handleCreateDevice = useCallback(
    async (data: DeviceCreate | DeviceUpdate) => {
      if (!('network_id' in data)) {
        return;
      }
      const createData: DeviceCreate = data;
      try {
        setIsSubmitting(true);
        await apiClient.createDevice(createData);

        toast({
          title: 'Device Created',
          description: `${createData.name} has been created successfully`,
        });

        setShowCreateModal(false);
        fetchDevices();
        onDeviceChanged?.();
      } catch (error: unknown) {
        const errorMessage = getErrorMessage(error, 'create device');
        // Don't close the dialog on error - let user see validation errors
        toast({
          title: getErrorTitle(error),
          description: errorMessage,
          variant: 'destructive',
        });
        // Re-throw to let DeviceForm handle fieldErrors
        throw error;
      } finally {
        setIsSubmitting(false);
      }
    },
    [fetchDevices, onDeviceChanged]
  );

  const { handleLockedErrorWithUnlock } = useLockedErrorHandler();

  const handleUpdateDevice = useCallback(
    async (data: DeviceCreate | DeviceUpdate) => {
      if (!selectedDevice) {
        toast({
          title: 'Error',
          description: 'No device selected for update',
          variant: 'destructive',
        });
        return;
      }
      if ('network_id' in data) {
        toast({
          title: 'Error',
          description: 'Cannot update network_id in edit mode',
          variant: 'destructive',
        });
        return;
      }
      const updateData: DeviceUpdate = data;

      try {
        setIsSubmitting(true);
        await apiClient.updateDevice(selectedDevice.id, updateData);

        toast({
          title: 'Device Updated',
          description: `${updateData.name} has been updated successfully`,
        });

        setShowEditModal(false);
        setSelectedDevice(null);
        fetchDevices();
        onDeviceChanged?.();
      } catch (error: unknown) {
        // Handle 423 locked error specially - show unlock modal instead of closing dialog
        if (handleLockedErrorWithUnlock(error)) {
          // Error was handled, modal is showing, Return without throwing
        }

        const errorMessage = getErrorMessage(error, 'update device');
        // Don't close dialog on error - let user see validation errors
        toast({
          title: getErrorTitle(error),
          description: errorMessage,
          variant: 'destructive',
        });
        // Re-throw to let DeviceForm handle fieldErrors
        throw error;
      } finally {
        setIsSubmitting(false);
      }
    },
    [selectedDevice, fetchDevices, onDeviceChanged, handleLockedErrorWithUnlock]
  );

  const handleDeleteDevice = useCallback(async () => {
    if (!selectedDevice) return;

    try {
      setIsSubmitting(true);
      await apiClient.deleteDevice(selectedDevice.id);

      toast({
        title: 'Device Deleted',
        description: `${selectedDevice.name} has been deleted successfully`,
      });

      setShowDeleteDialog(false);
      setSelectedDevice(null);
      fetchDevices();
      onDeviceChanged?.();
    } catch (error: unknown) {
      const errorMessage = getErrorMessage(error, 'delete device');
      toast({
        title: getErrorTitle(error),
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedDevice, fetchDevices, onDeviceChanged]);

  const handleRegenerateApiKey = useCallback(
    async (device: DeviceResponse) => {
      try {
        setIsSubmitting(true);
        setSelectedDevice(device);
        const response = await apiClient.regenerateDeviceApiKey(device.id);
        setNewApiKey(response.api_key);
        setShowApiKeyDialog(true);
        fetchDevices();
      } catch (error: unknown) {
        const errorMessage = getErrorMessage(error, 'regenerate API key');
        toast({
          title: getErrorTitle(error),
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [fetchDevices]
  );

  const handleRegenerateKeys = useCallback(
    async (device: DeviceResponse) => {
      try {
        setIsSubmitting(true);
        setSelectedDevice(device);
        const response = await apiClient.regenerateDeviceKeys(device.id, { method: 'cli' });
        setRegeneratedKeys(response);
        setShowRegenerateKeysDialog(true);
        fetchDevices();
      } catch (error: unknown) {
        const errorMessage = getErrorMessage(error, 'regenerate WireGuard keys');
        toast({
          title: getErrorTitle(error),
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [fetchDevices]
  );

  const openEditModal = useCallback((device: DeviceResponse) => {
    try {
      flushSync(() => {
        setSelectedDevice(device);
        setShowEditModal(true);
      });
    } catch (error) {
      console.error('Failed to open edit modal:', error);
      toast({
        title: 'Error',
        description: 'Failed to open edit dialog',
        variant: 'destructive',
      });
    }
  }, []);

  const openDeleteDialog = useCallback((device: DeviceResponse) => {
    setSelectedDevice(device);
    setShowDeleteDialog(true);
  }, []);

  const handleEditModalClose = useCallback((open: boolean) => {
    if (!open) {
      setSelectedDevice(null);
    }
    setShowEditModal(open);
  }, []);

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied to clipboard',
      description: 'The text has been copied to your clipboard',
    });
  }, []);

  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
      } else {
        setSortField(field);
        setSortDirection('asc');
      }
    },
    [sortField, sortDirection]
  );

  const clearFilters = useCallback(() => {
    setSearchQuery('');
    setLocationFilter('all');
    setEnabledFilter('all');
    setSortField('name');
    setSortDirection('asc');
  }, []);

  const sortedDevices = useMemo(() => {
    return [...devices].sort((a, b) => {
      const aValue = a[sortField] ?? '';
      const bValue = b[sortField] ?? '';

      const aCompare =
        typeof aValue === 'string' ? aValue.toLowerCase() : aValue;
      const bCompare =
        typeof bValue === 'string' ? bValue.toLowerCase() : bValue;

      if (sortDirection === 'asc') {
        return aCompare > bCompare ? 1 : -1;
      } else {
        return aCompare < bCompare ? 1 : -1;
      }
    });
  }, [devices, sortField, sortDirection]);

  if (initialLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Devices</CardTitle>
          <CardDescription>Connected devices for this network</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <Skeleton className="h-12 w-12 rounded-lg" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-[200px]" />
                  <Skeleton className="h-4 w-[150px]" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show loading state for refreshing/filtering but don't replace the entire UI
  const isRefreshing = fetching && !initialLoading;

  return (
    <>
      <Card>
        <CardHeader>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div>
                  <CardTitle>Devices</CardTitle>
                  <CardDescription>
                    Connected devices for this network
                  </CardDescription>
                </div>
                {isRefreshing && (
                  <RefreshCw className="h-4 w-4 text-muted-foreground animate-spin" />
                )}
              </div>
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Device
              </Button>
            </div>

            <DeviceFilters
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              locationFilter={locationFilter}
              onLocationChange={setLocationFilter}
              enabledFilter={enabledFilter}
              onEnabledChange={setEnabledFilter}
              sortField={sortField}
              sortDirection={sortDirection}
              onSortChange={handleSort}
              showFilters={showFilters}
              onShowFiltersChange={setShowFilters}
              onClearFilters={clearFilters}
              locations={locations}
            />
          </div>
        </CardHeader>

        {fetchError && (
          <div className="mx-6 mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
            <div>
              Could not load devices. There was an error fetching the data.
            </div>
            <div className="mt-2 text-xs text-red-800 dark:text-red-200">{fetchError}</div>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => fetchDevices()}
            >
              Retry
            </Button>
          </div>
        )}

        <CardContent>
          {initialLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-[200px]" />
                    <Skeleton className="h-4 w-[150px]" />
                  </div>
                </div>
              ))}
            </div>
          ) : fetchError && sortedDevices.length === 0 ? (
            <div className="text-center py-8">
              <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Failed to load devices</h3>
              <p className="text-muted-foreground mb-4">
                There was an error loading the devices list.
              </p>
              <div className="text-sm text-destructive mb-4">{fetchError}</div>
              <Button onClick={() => fetchDevices()}>
                Retry
              </Button>
            </div>
          ) : sortedDevices.length === 0 ? (
            <div className="text-center py-8">
              <Cpu className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No devices</h3>
              <p className="text-muted-foreground mb-4">
                {searchQuery || locationFilter || enabledFilter !== 'all'
                  ? 'No devices match your filters. Try adjusting them.'
                  : 'Add your first device to connect to this network'}
              </p>
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Device
              </Button>
            </div>
          ) : (
            <DevicesTable
              devices={sortedDevices}
              networkId={networkId}
              onEditDevice={openEditModal}
              onDeleteDevice={openDeleteDialog}
              onRegenerateApiKey={handleRegenerateApiKey}
              onRegenerateKeys={handleRegenerateKeys}
              onSort={handleSort}
              sortField={sortField}
              sortDirection={sortDirection}
            />
          )}
        </CardContent>
      </Card>

      {/* Device Forms */}
      <DeviceForm
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        onSubmit={handleCreateDevice}
        isSubmitting={isSubmitting}
        locations={locations}
        networkId={networkId}
        networkCidr={network?.network_cidr}
        mode="create"
      />

      <DeviceForm
        open={showEditModal}
        onOpenChange={handleEditModalClose}
        onSubmit={handleUpdateDevice}
        isSubmitting={isSubmitting}
        device={selectedDevice}
        locations={locations}
        networkId={networkId}
        networkCidr={network?.network_cidr}
        mode="edit"
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Device</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{selectedDevice?.name}
              &rdquo;? This action cannot be undone and will remove the device
              from the network.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <LoadingButton
              variant="destructive"
              onClick={handleDeleteDevice}
              loading={isSubmitting}
              loadingText="Deleting..."
            >
              Delete Device
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* API Key Dialog */}
      <Dialog open={showApiKeyDialog} onOpenChange={setShowApiKeyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>API Key Generated</span>
            </DialogTitle>
            <DialogDescription>
              A new API key has been generated for &ldquo;{selectedDevice?.name}
              &rdquo;. Copy this key now as it won&apos;t be shown again.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-4 bg-muted rounded-lg">
              <code className="text-sm break-all font-mono">{newApiKey}</code>
            </div>
            <Button
              onClick={() => copyToClipboard(newApiKey)}
              className="w-full"
              variant="outline"
            >
              Copy to Clipboard
            </Button>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowApiKeyDialog(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Regenerate Keys Dialog */}
      <Dialog open={showRegenerateKeysDialog} onOpenChange={setShowRegenerateKeysDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <RefreshCw className="h-5 w-5" />
              <span>WireGuard Keys Regenerated</span>
            </DialogTitle>
            <DialogDescription>
              New WireGuard keys have been generated for &ldquo;{selectedDevice?.name}
              &rdquo;. The device will need to use the new public key to connect.
            </DialogDescription>
          </DialogHeader>
          {regeneratedKeys && (
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="text-sm font-medium">New Public Key</div>
                <div className="p-3 bg-muted rounded-lg">
                  <code className="text-xs break-all font-mono">{regeneratedKeys.public_key}</code>
                </div>
              </div>
              <div className="p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
                <h4 className="font-semibold text-sm mb-2">Next Steps</h4>
                <ol className="text-sm space-y-1 list-decimal list-inside">
                  <li>Download the new configuration for this device</li>
                  <li>Update the device with the new public key</li>
                  <li>Restart the WireGuard interface on the device</li>
                  <li>Verify connection is established</li>
                </ol>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              onClick={() => setShowRegenerateKeysDialog(false)}
              className="w-full"
            >
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
