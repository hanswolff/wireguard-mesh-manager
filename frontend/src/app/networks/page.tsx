'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Plus,
  Search,
  SortAsc,
  SortDesc,
  MoreHorizontal,
  Edit,
  Trash2,
  Eye,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LoadingButton } from '@/components/ui/loading-button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertTriangle, MapPin, Cpu } from 'lucide-react';
import { FormErrorSummary } from '@/components/ui/form-error-summary';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import { useUnlock } from '@/contexts/unlock-context';
import apiClient, {
  type WireGuardNetworkListItem,
  type WireGuardNetworkCreate,
  type WireGuardNetworkUpdate,
} from '@/lib/api-client';
import Link from 'next/link';

type SortField =
  | 'name'
  | 'created_at'
  | 'updated_at'
  | 'device_count'
  | 'location_count';
type SortDirection = 'asc' | 'desc';

export default function NetworksPage() {
  const [networks, setNetworks] = useState<WireGuardNetworkListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedNetwork, setSelectedNetwork] =
    useState<WireGuardNetworkListItem | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeneratingPresharedKey, setIsGeneratingPresharedKey] =
    useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const { isUnlocked } = useUnlock();
  const cidrPattern = /^\d+\.\d+\.\d+\.\d+\/\d+$/;
  const errorLineClass = 'min-h-[1.25rem] text-sm text-destructive';
  const createNameRef = useRef<HTMLInputElement | null>(null);
  const createNetworkCidrRef = useRef<HTMLInputElement | null>(null);
  const createDnsServersRef = useRef<HTMLInputElement | null>(null);
  const createPresharedKeyRef = useRef<HTMLTextAreaElement | null>(null);
  const editNameRef = useRef<HTMLInputElement | null>(null);
  const editNetworkCidrRef = useRef<HTMLInputElement | null>(null);
  const editDnsServersRef = useRef<HTMLInputElement | null>(null);
  const editPresharedKeyRef = useRef<HTMLTextAreaElement | null>(null);

  // Form states
  const [formData, setFormData] = useState<WireGuardNetworkCreate>({
    name: '',
    description: '',
    network_cidr: '',
    dns_servers: '',
    mtu: undefined,
    persistent_keepalive: undefined,
    preshared_key: '',
    interface_properties: null,
  });

  useEffect(() => {
    if (!isUnlocked) {
      setLoading(false);
      return;
    }

    fetchNetworks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isUnlocked, searchQuery, sortField, sortDirection]);

  const updateField = <K extends keyof WireGuardNetworkCreate>(
    field: K,
    value: WireGuardNetworkCreate[K]
  ) => {
    setFormData((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => {
      if (!current[field as string]) {
        return current;
      }
      const next = { ...current };
      delete next[field as string];
      return next;
    });
  };

  const renderFieldError = (field: keyof WireGuardNetworkCreate) => {
    const message = formErrors[field as string];
    return (
      <p
        className={errorLineClass}
        {...(message ? { role: 'alert' } : { 'aria-hidden': true })}
      >
        {message ?? ''}
      </p>
    );
  };

  const formErrorMessages = Object.values(formErrors);

  const validateFormData = (data: Partial<WireGuardNetworkCreate>) => {
    const errors: Record<string, string> = {};
    if (!data.name) {
      errors.name = 'Name is required';
    }
    if (!data.network_cidr) {
      errors.network_cidr = 'Network CIDR is required';
    } else if (!cidrPattern.test(data.network_cidr)) {
      errors.network_cidr = 'Enter a valid CIDR (e.g. 10.0.0.0/24)';
    }
    return errors;
  };

  const focusFirstNetworkError = useCallback(
    (errors: Record<string, string>, mode: 'create' | 'edit') => {
      const fieldOrder = [
        'name',
        'network_cidr',
        'dns_servers',
        'preshared_key',
      ] as const;
      const refs =
        mode === 'edit'
          ? {
              name: editNameRef,
              network_cidr: editNetworkCidrRef,
              dns_servers: editDnsServersRef,
              preshared_key: editPresharedKeyRef,
            }
          : {
              name: createNameRef,
              network_cidr: createNetworkCidrRef,
              dns_servers: createDnsServersRef,
              preshared_key: createPresharedKeyRef,
            };

      for (const field of fieldOrder) {
        if (!errors[field]) continue;
        refs[field].current?.focus();
        break;
      }
    },
    [
      createNameRef,
      createNetworkCidrRef,
      createDnsServersRef,
      createPresharedKeyRef,
      editNameRef,
      editNetworkCidrRef,
      editDnsServersRef,
      editPresharedKeyRef,
    ]
  );

  const fetchNetworks = async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (searchQuery) params.search = searchQuery;

      const data = await apiClient.listNetworks(params);

      // Sort the data client-side since the API doesn't seem to support sorting parameters
      const sortedData = [...data].sort((a, b) => {
        let aValue: unknown = a[sortField as keyof typeof a];
        let bValue: unknown = b[sortField as keyof typeof b];

        if (aValue === null || aValue === undefined) aValue = '';
        if (bValue === null || bValue === undefined) bValue = '';

        if (typeof aValue === 'string') {
          aValue = aValue.toLowerCase();
          bValue = (bValue as string).toLowerCase();
        }

        const aStr = String(aValue);
        const bStr = String(bValue);

        if (sortDirection === 'asc') {
          return aStr > bStr ? 1 : -1;
        } else {
          return aStr < bStr ? 1 : -1;
        }
      });

      setNetworks(sortedData);
      setFetchError(null);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'An error occurred while loading networks';
      const isUnauthorized =
        typeof error === 'object' &&
        error !== null &&
        'isUnauthorized' in error &&
        Boolean((error as { isUnauthorized?: boolean }).isUnauthorized);

      if (isUnauthorized || !isUnlocked) {
        setShowUnlockModal(true);
      }
      setFetchError(message);
      toast({
        title: 'Failed to fetch networks',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNetwork = async () => {
    const validationErrors = validateFormData(formData);

    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors);
      focusFirstNetworkError(validationErrors, 'create');
      toast({
        title: 'Validation Error',
        description: 'Name and network CIDR are required',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsSubmitting(true);
      setFormErrors({});
      const createData: WireGuardNetworkCreate = {
        name: formData.name,
        description: formData.description,
        network_cidr: formData.network_cidr,
        dns_servers: formData.dns_servers,
        mtu: formData.mtu,
        persistent_keepalive: formData.persistent_keepalive,
        preshared_key: formData.preshared_key?.trim() || undefined,
        interface_properties: formData.interface_properties,
      };
      await apiClient.createNetwork(createData);

      toast({
        title: 'Network Created',
        description: `${formData.name} has been created successfully`,
      });

      setShowCreateModal(false);
      resetForm();
      fetchNetworks();
    } catch (error) {
      const fieldErrors = (error as { fieldErrors?: Record<string, string> })
        .fieldErrors;
      const errorData = (error as { data?: { message?: string; error?: string } }).data;

      if (fieldErrors && Object.keys(fieldErrors).length > 0) {
        setFormErrors(fieldErrors);
        focusFirstNetworkError(fieldErrors, 'create');
      } else {
        // Extract backend error message from error data
        let backendMessage: string | undefined;
        if (errorData?.message) {
          backendMessage = errorData.message;
        } else if (errorData?.error) {
          backendMessage = errorData.error;
        }

        if (backendMessage) {
          setFormErrors({ general: backendMessage });
        }
      }

      toast({
        title: 'Create Failed',
        description:
          error instanceof Error ? error.message : 'Failed to create network',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateNetwork = async () => {
    if (!selectedNetwork) {
      return;
    }

    const validationErrors = validateFormData(formData);

    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors);
      focusFirstNetworkError(validationErrors, 'edit');
      toast({
        title: 'Validation Error',
        description: 'Name and network CIDR are required',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsSubmitting(true);
      setFormErrors({});
      const updateData: WireGuardNetworkUpdate = {
        name: formData.name,
        description: formData.description,
        network_cidr: formData.network_cidr,
        dns_servers: formData.dns_servers,
        mtu: formData.mtu,
        persistent_keepalive: formData.persistent_keepalive,
        preshared_key: formData.preshared_key?.trim() || undefined,
      };

      await apiClient.updateNetwork(selectedNetwork.id, updateData);

      toast({
        title: 'Network Updated',
        description: `${formData.name} has been updated successfully`,
      });

      setShowEditModal(false);
      resetForm();
      fetchNetworks();
    } catch (error) {
      const fieldErrors = (error as { fieldErrors?: Record<string, string> })
        .fieldErrors;
      const errorData = (error as { data?: { message?: string; error?: string } }).data;

      if (fieldErrors && Object.keys(fieldErrors).length > 0) {
        setFormErrors(fieldErrors);
        focusFirstNetworkError(fieldErrors, 'edit');
      } else {
        // Extract backend error message from error data
        let backendMessage: string | undefined;
        if (errorData?.message) {
          backendMessage = errorData.message;
        } else if (errorData?.error) {
          backendMessage = errorData.error;
        }

        if (backendMessage) {
          setFormErrors({ general: backendMessage });
        }
      }

      toast({
        title: 'Update Failed',
        description:
          error instanceof Error ? error.message : 'Failed to update network',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteNetwork = async () => {
    if (!selectedNetwork) return;

    try {
      setIsSubmitting(true);
      await apiClient.deleteNetwork(selectedNetwork.id);

      toast({
        title: 'Network Deleted',
        description: `${selectedNetwork.name} has been deleted successfully`,
      });

      setShowDeleteDialog(false);
      setSelectedNetwork(null);
      fetchNetworks();
    } catch (error) {
      toast({
        title: 'Delete Failed',
        description:
          error instanceof Error ? error.message : 'Failed to delete network',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      network_cidr: '',
      dns_servers: '',
      mtu: undefined,
      persistent_keepalive: undefined,
      preshared_key: '',
      interface_properties: null,
    });
    setFormErrors({});
    setSelectedNetwork(null);
  };

  const openEditModal = (network: WireGuardNetworkListItem) => {
    setSelectedNetwork(network);
    setFormErrors({});
    setFormData({
      name: network.name,
      description: network.description || '',
      network_cidr: network.network_cidr,
      dns_servers: network.dns_servers || '',
      mtu: network.mtu ?? undefined,
      persistent_keepalive: network.persistent_keepalive ?? undefined,
      preshared_key: '',
      interface_properties: network.interface_properties || null,
    });
    setShowEditModal(true);
  };

  const handleGeneratePresharedKey = async () => {
    try {
      setIsGeneratingPresharedKey(true);
      const response = await apiClient.generateWireGuardPresharedKey();
      updateField('preshared_key', response.preshared_key);
      toast({
        title: 'Preshared Key Generated',
        description: 'A new preshared key has been generated.',
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Failed to generate preshared key';
      toast({
        title: 'Generation Failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsGeneratingPresharedKey(false);
    }
  };

  const openDeleteDialog = (network: WireGuardNetworkListItem) => {
    setSelectedNetwork(network);
    setShowDeleteDialog(true);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <SortAsc className="h-4 w-4" />;
    }
    return sortDirection === 'asc' ? (
      <SortAsc className="h-4 w-4" />
    ) : (
      <SortDesc className="h-4 w-4" />
    );
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-3">
          <Globe className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Networks</h1>
            <p className="text-muted-foreground">
              Manage your WireGuard networks
            </p>
          </div>
        </div>
        <div className="grid gap-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-[250px]" />
                    <Skeleton className="h-4 w-[200px]" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <MasterPasswordUnlockModal
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
        onSuccess={() => fetchNetworks()}
        title="Unlock to view networks"
        description="Enter the master password to load and manage networks."
      />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Globe className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Networks</h1>
            <p className="text-muted-foreground">
              Manage your WireGuard networks
            </p>
          </div>
        </div>
        <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Network
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Create New Network</DialogTitle>
              <DialogDescription>
                Create a new WireGuard network. Configure the basic network
                settings.
              </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <FormErrorSummary messages={formErrorMessages} />
            <div className="grid gap-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                  id="name"
                  ref={createNameRef}
                  value={formData.name}
                  onChange={(e) => updateField('name', e.target.value)}
                  placeholder="Enter network name"
                  disabled={isSubmitting}
                />
                {renderFieldError('name')}
              </div>
              <div className="grid gap-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description ?? ''}
                  onChange={(e) => updateField('description', e.target.value)}
                  placeholder="Enter network description"
                  rows={3}
                  disabled={isSubmitting}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="network_cidr">Network CIDR *</Label>
                <Input
                  id="network_cidr"
                  ref={createNetworkCidrRef}
                  value={formData.network_cidr}
                  onChange={(e) => updateField('network_cidr', e.target.value)}
                  placeholder="10.0.0.0/24"
                  disabled={isSubmitting}
                />
                {renderFieldError('network_cidr')}
              </div>
              <div className="grid gap-2">
                <Label htmlFor="dns_servers">DNS Servers</Label>
                <Input
                  id="dns_servers"
                  ref={createDnsServersRef}
                  value={formData.dns_servers ?? ''}
                  onChange={(e) =>
                    updateField('dns_servers', e.target.value)
                  }
                  placeholder="1.1.1.1, 8.8.8.8"
                  disabled={isSubmitting}
                />
                {renderFieldError('dns_servers')}
              </div>
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="preshared_key">Preshared Key (Optional)</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleGeneratePresharedKey}
                    disabled={isSubmitting || isGeneratingPresharedKey}
                  >
                    {isGeneratingPresharedKey ? 'Generating...' : 'Generate'}
                  </Button>
                </div>
                <Textarea
                  id="preshared_key"
                  ref={createPresharedKeyRef}
                  value={formData.preshared_key ?? ''}
                  onChange={(e) =>
                    updateField('preshared_key', e.target.value)
                  }
                  placeholder="Paste a WireGuard preshared key"
                  rows={3}
                  disabled={isSubmitting}
                />
                {renderFieldError('preshared_key')}
                <p className="text-xs text-muted-foreground">
                  Default preshared key for locations and devices in this
                  network.
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowCreateModal(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <LoadingButton
                onClick={handleCreateNetwork}
                loading={isSubmitting}
                loadingText="Creating..."
              >
                Create Network
              </LoadingButton>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      {fetchError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div>
            Could not refresh the networks list. The view may be stale. Retry
            or reload the page.
          </div>
          <div className="mt-2 text-xs text-amber-800">{fetchError}</div>
        </div>
      )}

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center space-x-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search networks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                aria-label="Search networks"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Networks List */}
      {fetchError && networks.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <div
              className="text-lg font-semibold mb-2"
              role="heading"
              aria-level={2}
            >
              Failed to load networks
            </div>
            <p className="text-muted-foreground mb-4">
              There was an error loading the networks list.
            </p>
            <div className="text-sm text-destructive mb-4">{fetchError}</div>
            <Button onClick={() => fetchNetworks()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : networks.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Globe className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <div
              className="text-lg font-semibold mb-2"
              role="heading"
              aria-level={2}
            >
              No networks found
            </div>
            <p className="text-muted-foreground mb-4">
              {searchQuery
                ? 'Try adjusting your search terms'
                : 'Get started by creating your first network'}
            </p>
            {!searchQuery && (
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Network
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Networks ({networks.length})</CardTitle>
            <CardDescription>
              Manage your WireGuard networks and their configurations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <caption className="sr-only">
                Networks table with sorting capabilities
              </caption>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('name')}
                    aria-sort={
                      sortField === 'name'
                        ? sortDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none'
                    }
                  >
                    <div className="flex items-center space-x-1">
                      <span>Name</span>
                      {getSortIcon('name')}
                    </div>
                  </TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Network CIDR</TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('location_count')}
                    aria-sort={
                      sortField === 'location_count'
                        ? sortDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none'
                    }
                  >
                    <div className="flex items-center space-x-1">
                      <MapPin className="h-4 w-4" />
                      <span>Locations</span>
                      {getSortIcon('location_count')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('device_count')}
                    aria-sort={
                      sortField === 'device_count'
                        ? sortDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none'
                    }
                  >
                    <div className="flex items-center space-x-1">
                      <Cpu className="h-4 w-4" />
                      <span>Devices</span>
                      {getSortIcon('device_count')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('created_at')}
                    aria-sort={
                      sortField === 'created_at'
                        ? sortDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none'
                    }
                  >
                    <div className="flex items-center space-x-1">
                      <span>Created</span>
                      {getSortIcon('created_at')}
                    </div>
                  </TableHead>
                  <TableHead className="w-[70px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {networks.map((network) => (
                  <TableRow key={network.id} className="hover:bg-muted/50">
                    <TableCell>
                      <div>
                        <Link
                          href={`/networks/${network.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {network.name}
                        </Link>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-[200px] truncate">
                        {network.description || (
                          <span className="text-muted-foreground">
                            No description
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {network.network_cidr}
                      </code>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">
                          {network.location_count}
                        </span>
                        <span className="text-muted-foreground text-sm">
                          locations
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">
                          {network.device_count}
                        </span>
                        <span className="text-muted-foreground text-sm">
                          devices
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-muted-foreground">
                        {network.created_at
                          ? new Date(network.created_at).toLocaleDateString()
                          : '—'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link href={`/networks/${network.id}`}>
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => openEditModal(network)}
                          >
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => openDeleteDialog(network)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Edit Modal */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Network</DialogTitle>
            <DialogDescription>
              Update the network configuration for {selectedNetwork?.name}.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <FormErrorSummary messages={formErrorMessages} />
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Name *</Label>
              <Input
                id="edit-name"
                ref={editNameRef}
                value={formData.name}
                onChange={(e) => updateField('name', e.target.value)}
                placeholder="Enter network name"
                disabled={isSubmitting}
              />
              {renderFieldError('name')}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description ?? ''}
                onChange={(e) => updateField('description', e.target.value)}
                placeholder="Enter network description"
                rows={3}
                disabled={isSubmitting}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-network_cidr">Network CIDR *</Label>
              <Input
                id="edit-network_cidr"
                ref={editNetworkCidrRef}
                value={formData.network_cidr}
                onChange={(e) => updateField('network_cidr', e.target.value)}
                placeholder="10.0.0.0/24"
                disabled={isSubmitting}
              />
              {renderFieldError('network_cidr')}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-dns_servers">DNS Servers</Label>
              <Input
                id="edit-dns_servers"
                ref={editDnsServersRef}
                value={formData.dns_servers ?? ''}
                onChange={(e) => updateField('dns_servers', e.target.value)}
                placeholder="1.1.1.1, 8.8.8.8"
                disabled={isSubmitting}
              />
              {renderFieldError('dns_servers')}
            </div>
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="edit-preshared_key">
                  Preshared Key (Optional)
                </Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleGeneratePresharedKey}
                  disabled={isSubmitting || isGeneratingPresharedKey}
                >
                  {isGeneratingPresharedKey ? 'Generating...' : 'Generate'}
                </Button>
              </div>
              <Textarea
                id="edit-preshared_key"
                ref={editPresharedKeyRef}
                value={formData.preshared_key ?? ''}
                onChange={(e) =>
                  updateField('preshared_key', e.target.value)
                }
                placeholder="Paste a WireGuard preshared key"
                rows={3}
                disabled={isSubmitting}
              />
              {renderFieldError('preshared_key')}
              <p className="text-xs text-muted-foreground">
                Default preshared key for locations and devices in this
                network.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowEditModal(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <LoadingButton
              onClick={handleUpdateNetwork}
              loading={isSubmitting}
              loadingText="Updating..."
            >
              Update Network
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              <span>Delete Network</span>
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{selectedNetwork?.name}
              &rdquo;? This action cannot be undone and will remove all
              locations, devices, and configurations associated with this
              network.
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
              onClick={handleDeleteNetwork}
              loading={isSubmitting}
              loadingText="Deleting..."
            >
              Delete Network
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
