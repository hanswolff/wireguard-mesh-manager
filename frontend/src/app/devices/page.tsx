'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import {
  Plus,
  Search,
  Cpu,
  Globe,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import apiClient, {
  type DeviceResponse,
  type DeviceCreate,
  type DeviceUpdate,
  type DeviceKeysRegenerateResponse,
  type LocationResponse,
  type WireGuardNetworkListItem,
} from '@/lib/api-client';
import DevicesTable from '@/app/networks/[id]/components/devices-table';
import DeviceForm from '@/app/networks/[id]/components/device-form';

export default function DevicesPage() {
  // Data state
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [networks, setNetworks] = useState<WireGuardNetworkListItem[]>([]);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // UI state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [networkFilter, setNetworkFilter] = useState<string>('all');
  const [enabledFilter, setEnabledFilter] = useState<'all' | 'true' | 'false'>('all');
  const [expandedNetworks, setExpandedNetworks] = useState<Set<string>>(new Set());
  const [selectedNetworkForCreate, setSelectedNetworkForCreate] = useState<string>('');
  const [selectedLocationForCreate, setSelectedLocationForCreate] = useState<string>('');
  const [selectedDevice, setSelectedDevice] = useState<DeviceResponse | null>(null);
  const [showApiKeyDialog, setShowApiKeyDialog] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  const [showRegenerateKeysDialog, setShowRegenerateKeysDialog] = useState(false);
  const [regeneratedKeys, setRegeneratedKeys] = useState<DeviceKeysRegenerateResponse | null>(
    null
  );

  // Fetch all data
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-expand networks when devices are loaded
  useEffect(() => {
    if (devices.length > 0 && expandedNetworks.size === 0) {
      const networkIds = [...new Set(devices.map((d) => d.network_id))];
      setExpandedNetworks(new Set(networkIds));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devices]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [devicesData, networksData, locationsData] = await Promise.all([
        apiClient.listDevices(),
        apiClient.listNetworks(),
        apiClient.listLocations(),
      ]);

      setDevices(devicesData);
      setNetworks(networksData);
      setLocations(locationsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      setError(message);
      toast({
        title: 'Error loading devices',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // Filter devices
  const filteredDevices = useMemo(() => {
    return devices.filter((device) => {
      // Network filter
      if (networkFilter !== 'all' && device.network_id !== networkFilter) {
        return false;
      }

      // Status filter
      if (enabledFilter !== 'all') {
        const isEnabled = enabledFilter === 'true';
        if (device.enabled !== isEnabled) {
          return false;
        }
      }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesName = device.name.toLowerCase().includes(query);
        const matchesDesc =
          device.description?.toLowerCase().includes(query) ?? false;
        const matchesIp = device.wireguard_ip?.includes(query) ?? false;
        const matchesLocation =
          device.location_name?.toLowerCase().includes(query) ?? false;

        if (!matchesName && !matchesDesc && !matchesIp && !matchesLocation) {
          return false;
        }
      }

      return true;
    });
  }, [devices, networkFilter, enabledFilter, searchQuery]);

  // Group devices by network
  const devicesByNetwork = useMemo(() => {
    const grouped = new Map<string, DeviceResponse[]>();
    filteredDevices.forEach((device) => {
      if (!grouped.has(device.network_id)) {
        grouped.set(device.network_id, []);
      }
      grouped.get(device.network_id)!.push(device);
    });
    return grouped;
  }, [filteredDevices]);

  // Sort devices within each network
  const sortedDevicesByNetwork = useMemo(() => {
    const result = new Map<string, DeviceResponse[]>();
    devicesByNetwork.forEach((devs, networkId) => {
      const sorted = [...devs].sort((a, b) => {
        const aName = a.name.toLowerCase();
        const bName = b.name.toLowerCase();
        return aName > bName ? 1 : -1;
      });
      result.set(networkId, sorted);
    });
    return result;
  }, [devicesByNetwork]);

  // Sort networks alphabetically
  const sortedNetworkIds = useMemo(() => {
    const ids = Array.from(devicesByNetwork.keys());
    return ids.sort((a, b) => {
      const networkA = networks.find((n) => n.id === a);
      const networkB = networks.find((n) => n.id === b);
      const nameA = networkA?.name.toLowerCase() || a;
      const nameB = networkB?.name.toLowerCase() || b;
      return nameA > nameB ? 1 : -1;
    });
  }, [devicesByNetwork, networks]);

  // Calculate stats
  const stats = useMemo(() => {
    const totalDevices = devices.length;
    const enabledDevices = devices.filter((d) => d.enabled).length;
    const networksWithDevices = new Set(devices.map((d) => d.network_id)).size;
    return { totalDevices, enabledDevices, networksWithDevices };
  }, [devices]);

  // Toggle network expansion
  const toggleNetwork = useCallback((networkId: string) => {
    setExpandedNetworks((prev) => {
      const next = new Set(prev);
      if (next.has(networkId)) {
        next.delete(networkId);
      } else {
        next.add(networkId);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    const allNetworkIds = Array.from(devicesByNetwork.keys());
    setExpandedNetworks(new Set(allNetworkIds));
  }, [devicesByNetwork]);

  const collapseAll = useCallback(() => {
    setExpandedNetworks(new Set());
  }, []);

  const handleRegenerateApiKey = useCallback(
    async (device: DeviceResponse) => {
      try {
        setIsSubmitting(true);
        setSelectedDevice(device);
        const response = await apiClient.regenerateDeviceApiKey(device.id);
        setNewApiKey(response.api_key);
        setShowApiKeyDialog(true);
        fetchData();
      } catch (error: unknown) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : 'Failed to regenerate API key';
        toast({
          title: 'API Key Generation Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [fetchData]
  );

  const handleRegenerateKeys = useCallback(
    async (device: DeviceResponse) => {
      try {
        setIsSubmitting(true);
        setSelectedDevice(device);
        const response = await apiClient.regenerateDeviceKeys(device.id, { method: 'cli' });
        setRegeneratedKeys(response);
        setShowRegenerateKeysDialog(true);
        fetchData();
      } catch (error: unknown) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : 'Failed to regenerate WireGuard keys';
        toast({
          title: 'Key Regeneration Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [fetchData]
  );

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied to clipboard',
      description: 'The text has been copied to your clipboard',
    });
  }, []);

  // Handle device creation
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
        setSelectedNetworkForCreate('');
        setSelectedLocationForCreate('');
        fetchData();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create device';
        toast({
          title: 'Create Failed',
          description: message,
          variant: 'destructive',
        });
        // Re-throw to let DeviceForm handle fieldErrors
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [fetchData]
  );

  // Clear filters
  const clearFilters = useCallback(() => {
    setSearchQuery('');
    setNetworkFilter('all');
    setEnabledFilter('all');
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Cpu className="h-8 w-8 text-primary" />
            <div>
              <Skeleton className="h-8 w-[200px]" />
              <Skeleton className="h-4 w-[300px] mt-2" />
            </div>
          </div>
          <Skeleton className="h-10 w-[120px]" />
        </div>

        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-[150px]" />
          </CardHeader>
          <CardContent className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-[250px]" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-12 w-full" />
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-3">
          <Cpu className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Devices</h1>
            <p className="text-muted-foreground">
              View and manage all devices across all networks
            </p>
          </div>
        </div>

        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>

        <Button onClick={fetchData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Cpu className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Devices</h1>
            <p className="text-muted-foreground">
              View and manage all devices across all networks
            </p>
          </div>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Device
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDevices}</div>
            <p className="text-xs text-muted-foreground">across all networks</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Enabled</CardTitle>
            <div className="h-2 w-2 rounded-full bg-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.enabledDevices}</div>
            <p className="text-xs text-muted-foreground">
              {stats.totalDevices > 0
                ? `${Math.round((stats.enabledDevices / stats.totalDevices) * 100)}% of total`
                : '0% of total'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Networks</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.networksWithDevices}</div>
            <p className="text-xs text-muted-foreground">with devices</p>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search devices by name, description, or IP..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>

              <Select value={networkFilter} onValueChange={setNetworkFilter}>
                <SelectTrigger className="w-full sm:w-[250px]">
                  <SelectValue placeholder="Filter by network" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All networks</SelectItem>
                  {networks.map((network) => (
                    <SelectItem key={network.id} value={network.id}>
                      {network.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={enabledFilter}
                onValueChange={(value: 'all' | 'true' | 'false') =>
                  setEnabledFilter(value)
                }
              >
                <SelectTrigger className="w-full sm:w-[150px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All status</SelectItem>
                  <SelectItem value="true">Enabled</SelectItem>
                  <SelectItem value="false">Disabled</SelectItem>
                </SelectContent>
              </Select>

              {(searchQuery || networkFilter !== 'all' || enabledFilter !== 'all') && (
                <Button variant="outline" onClick={clearFilters}>
                  Clear
                </Button>
              )}
            </div>

            {/* Expand/Collapse all buttons */}
            {sortedNetworkIds.length > 1 && (
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={expandAll}>
                  Expand All
                </Button>
                <Button variant="ghost" size="sm" onClick={collapseAll}>
                  Collapse All
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Devices grouped by network */}
      {sortedNetworkIds.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Cpu className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <div className="text-lg font-semibold mb-2">No devices found</div>
            <p className="text-muted-foreground mb-4">
              {searchQuery || networkFilter !== 'all' || enabledFilter !== 'all'
                ? 'No devices match your filters. Try adjusting them.'
                : stats.totalDevices === 0
                ? 'Add your first device to get started'
                : 'No devices match your criteria'}
            </p>
            {stats.totalDevices === 0 && (
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Device
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {sortedNetworkIds.map((networkId) => {
            const network = networks.find((n) => n.id === networkId);
            const networkDevices = sortedDevicesByNetwork.get(networkId) || [];
            const isExpanded = expandedNetworks.has(networkId);

            return (
              <Card key={networkId}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleNetwork(networkId)}
                        className="p-0 h-6 w-6"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>

                      <div className="flex-1">
                        <Link
                          href={`/networks/${networkId}`}
                          className="font-semibold hover:text-primary hover:underline"
                        >
                          {network?.name || networkId}
                        </Link>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                          <Badge variant="outline" className="text-xs">
                            {network?.network_cidr || 'Unknown CIDR'}
                          </Badge>
                          <span>•</span>
                          <span>{networkDevices.length} device{networkDevices.length !== 1 ? 's' : ''}</span>
                        </div>
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedNetworkForCreate(networkId);
                        setShowCreateModal(true);
                      }}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      Add Device
                    </Button>
                  </div>
                </CardHeader>

                {isExpanded && (
                  <CardContent className="pt-0">
                    {networkDevices.length === 0 ? (
                      <div className="text-center py-8">
                        <Cpu className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
                        <h3 className="text-sm font-medium mb-1">No devices in this network</h3>
                        <p className="text-xs text-muted-foreground mb-3">
                          Add your first device to this network
                        </p>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setSelectedNetworkForCreate(networkId);
                            setShowCreateModal(true);
                          }}
                        >
                          <Plus className="h-3 w-3 mr-1" />
                          Add Device
                        </Button>
                      </div>
                    ) : (
                      <DevicesTable
                        devices={networkDevices}
                        networkId={networkId}
                        onEditDevice={() => {}}
                        onDeleteDevice={() => {}}
                        onRegenerateApiKey={handleRegenerateApiKey}
                        onRegenerateKeys={handleRegenerateKeys}
                        onSort={() => {}}
                        sortField="name"
                        sortDirection="asc"
                      />
                    )}
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Device Dialog */}
      <DeviceForm
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        onSubmit={handleCreateDevice}
        isSubmitting={isSubmitting}
        locations={locations}
        networkId={selectedNetworkForCreate}
        networkCidr={
          networks.find((n) => n.id === selectedNetworkForCreate)?.network_cidr
        }
        mode="create"
        preselectedNetworkId={selectedNetworkForCreate}
        preselectedLocationId={selectedLocationForCreate}
      />

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
    </div>
  );
}
