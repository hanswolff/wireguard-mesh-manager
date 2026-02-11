'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, MapPin, Edit, Trash2, MoreHorizontal, AlertTriangle } from 'lucide-react';
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
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { InterfacePropertiesForm } from '@/components/ui/interface-properties-form';
import { FormErrorSummary } from '@/components/ui/form-error-summary';
import apiClient, {
  type LocationResponse,
  type LocationCreate,
  type LocationUpdate,
} from '@/lib/api-client';

interface NetworkLocationsProps {
  networkId: string;
  onLocationChanged?: () => void;
}

export default function NetworkLocations({ networkId, onLocationChanged }: NetworkLocationsProps) {
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedLocation, setSelectedLocation] =
    useState<LocationResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeneratingPresharedKey, setIsGeneratingPresharedKey] =
    useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const errorLineClass = 'min-h-[1.25rem] text-sm text-destructive';
  const createNameRef = useRef<HTMLInputElement | null>(null);
  const createExternalEndpointRef = useRef<HTMLInputElement | null>(null);
  const createPresharedKeyRef = useRef<HTMLTextAreaElement | null>(null);
  const editNameRef = useRef<HTMLInputElement | null>(null);
  const editExternalEndpointRef = useRef<HTMLInputElement | null>(null);
  const editPresharedKeyRef = useRef<HTMLTextAreaElement | null>(null);

  // Form states
  const [formData, setFormData] = useState<LocationCreate>({
    network_id: networkId,
    name: '',
    description: '',
    external_endpoint: '',
    preshared_key: '',
    interface_properties: null,
  });

  const updateField = <K extends keyof LocationCreate>(
    field: K,
    value: LocationCreate[K]
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

  const renderFieldError = (field: keyof LocationCreate) => {
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

  const focusFirstLocationError = useCallback(
    (errors: Record<string, string>, mode: 'create' | 'edit') => {
      const fieldOrder = ['name', 'external_endpoint', 'preshared_key'] as const;
      const refs =
        mode === 'edit'
          ? {
              name: editNameRef,
              external_endpoint: editExternalEndpointRef,
              preshared_key: editPresharedKeyRef,
            }
          : {
              name: createNameRef,
              external_endpoint: createExternalEndpointRef,
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
      createExternalEndpointRef,
      createPresharedKeyRef,
      editNameRef,
      editExternalEndpointRef,
      editPresharedKeyRef,
    ]
  );

  const fetchLocations = useCallback(async () => {
    try {
      setLoading(true);
      setFetchError(null);
      const data = await apiClient.listLocations({ network_id: networkId });
      setLocations(data);
      setFetchError(null);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'An error occurred while loading locations';
      setFetchError(message);
      toast({
        title: 'Failed to fetch locations',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [networkId]);

  useEffect(() => {
    fetchLocations();
  }, [fetchLocations]);

  const handleCreateLocation = useCallback(async () => {
    const validationErrors: Record<string, string> = {};
    if (!formData.name) {
      validationErrors.name = 'Name is required';
    }

    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors);
      focusFirstLocationError(validationErrors, 'create');
      toast({
        title: 'Validation Error',
        description: 'Please correct the highlighted fields',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsSubmitting(true);
      setFormErrors({});
      const createData: LocationCreate = {
        ...formData,
        external_endpoint: formData.external_endpoint?.trim() || undefined,
        preshared_key: formData.preshared_key?.trim() || undefined,
      };
      await apiClient.createLocation(createData);

      toast({
        title: 'Location Created',
        description: `${formData.name} has been created successfully`,
      });

      setShowCreateModal(false);
      setFormData({
        network_id: networkId,
        name: '',
        description: '',
        external_endpoint: '',
        preshared_key: '',
        interface_properties: null,
      });
      setFormErrors({});
      setSelectedLocation(null);
      fetchLocations();
      onLocationChanged?.();
    } catch (error) {
      const fieldErrors = (error as { fieldErrors?: Record<string, string> })
        .fieldErrors;
      if (fieldErrors && Object.keys(fieldErrors).length > 0) {
        setFormErrors(fieldErrors);
        focusFirstLocationError(fieldErrors, 'create');
      }
      toast({
        title: 'Create Failed',
        description:
          error instanceof Error ? error.message : 'Failed to create location',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, fetchLocations, onLocationChanged, networkId]);

  const handleUpdateLocation = useCallback(async () => {
    if (!selectedLocation) {
      return;
    }

    const validationErrors: Record<string, string> = {};
    if (!formData.name) {
      validationErrors.name = 'Name is required';
    }

    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors);
      focusFirstLocationError(validationErrors, 'edit');
      toast({
        title: 'Validation Error',
        description: 'Please correct the highlighted fields',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsSubmitting(true);
      setFormErrors({});
      const updateData: LocationUpdate = {
        name: formData.name,
        description: formData.description,
        external_endpoint: formData.external_endpoint?.trim() || undefined,
        preshared_key: formData.preshared_key?.trim() || undefined,
        interface_properties: formData.interface_properties,
      };

      await apiClient.updateLocation(selectedLocation.id, updateData);

      toast({
        title: 'Location Updated',
        description: `${formData.name} has been updated successfully`,
      });

      setShowEditModal(false);
      setFormData({
        network_id: networkId,
        name: '',
        description: '',
        external_endpoint: '',
        preshared_key: '',
        interface_properties: null,
      });
      setFormErrors({});
      setSelectedLocation(null);
      fetchLocations();
      onLocationChanged?.();
    } catch (error) {
      const fieldErrors = (error as { fieldErrors?: Record<string, string> })
        .fieldErrors;
      if (fieldErrors && Object.keys(fieldErrors).length > 0) {
        setFormErrors(fieldErrors);
        focusFirstLocationError(fieldErrors, 'edit');
      }
      toast({
        title: 'Update Failed',
        description:
          error instanceof Error ? error.message : 'Failed to update location',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, selectedLocation, fetchLocations, onLocationChanged, networkId]);

  const handleDeleteLocation = useCallback(async () => {
    if (!selectedLocation) return;

    try {
      setIsSubmitting(true);
      await apiClient.deleteLocation(selectedLocation.id);

      toast({
        title: 'Location Deleted',
        description: `${selectedLocation.name} has been deleted successfully`,
      });

      setShowDeleteDialog(false);
      setSelectedLocation(null);
      fetchLocations();
      onLocationChanged?.();
    } catch (error) {
      toast({
        title: 'Delete Failed',
        description:
          error instanceof Error ? error.message : 'Failed to delete location',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedLocation, fetchLocations, onLocationChanged]);

  const openEditModal = (location: LocationResponse) => {
    setSelectedLocation(location);
    setFormErrors({});
    setFormData({
      network_id: networkId,
      name: location.name,
      description: location.description || '',
      external_endpoint: location.external_endpoint || '',
      preshared_key: '',
      interface_properties: location.interface_properties || null,
    });
    setShowEditModal(true);
  };

  const handleGeneratePresharedKey = useCallback(async () => {
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
  }, [updateField]);

  const openDeleteDialog = (location: LocationResponse) => {
    setSelectedLocation(location);
    setShowDeleteDialog(true);
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Locations</CardTitle>
          <CardDescription>Network endpoint locations</CardDescription>
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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Locations</CardTitle>
            <CardDescription>
              Network endpoint locations for this network
            </CardDescription>
          </div>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Location
          </Button>
        </div>
      </CardHeader>

      {/* Create Location Modal */}
      <Dialog
        open={showCreateModal}
        onOpenChange={(open) => {
          setShowCreateModal(open);
          if (open) {
            setFormErrors({});
          }
        }}
      >
        <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add New Location</DialogTitle>
            <DialogDescription>
              Add a new location endpoint for this network.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <FormErrorSummary messages={Object.values(formErrors)} />
            <div className="grid gap-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                ref={createNameRef}
                value={formData.name || ''}
                onChange={(e) =>
                  updateField('name', e.target.value)
                }
                placeholder="Enter location name"
                disabled={isSubmitting}
              />
              {renderFieldError('name')}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description || ''}
                onChange={(e) =>
                  updateField('description', e.target.value)
                }
                placeholder="Enter location description"
                rows={3}
                disabled={isSubmitting}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="external_endpoint">External Endpoint</Label>
              <Input
                id="external_endpoint"
                ref={createExternalEndpointRef}
                value={formData.external_endpoint || ''}
                onChange={(e) =>
                  updateField('external_endpoint', e.target.value)
                }
                placeholder="vpn.example.com"
                disabled={isSubmitting}
              />
              <p className="text-xs text-muted-foreground">
                Hostname or IP address (no port)
              </p>
              {renderFieldError('external_endpoint')}
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
            </div>
            <div className="col-span-2">
              <InterfacePropertiesForm
                value={formData.interface_properties}
                onChange={(properties) =>
                  updateField('interface_properties', properties)
                }
                disabled={isSubmitting}
                level="location"
              />
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
              onClick={handleCreateLocation}
              loading={isSubmitting}
              loadingText="Creating..."
            >
              Add Location
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {fetchError && (
        <div className="mx-6 mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
          <div>
            Could not load locations. There was an error fetching the data.
          </div>
          <div className="mt-2 text-xs text-red-800 dark:text-red-200">{fetchError}</div>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => fetchLocations()}
          >
            Retry
          </Button>
        </div>
      )}

      <CardContent>
        {fetchError && locations.length === 0 ? (
          <div className="text-center py-8">
            <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to load locations</h3>
            <p className="text-muted-foreground mb-4">
              There was an error loading the locations list.
            </p>
            <div className="text-sm text-destructive mb-4">{fetchError}</div>
            <Button onClick={() => fetchLocations()}>
              Retry
            </Button>
          </div>
        ) : locations.length === 0 ? (
          <div className="text-center py-8">
            <MapPin className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No locations</h3>
            <p className="text-muted-foreground mb-4">
              Add your first location to define network endpoints
            </p>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Location
            </Button>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>External Endpoint</TableHead>
                <TableHead>Devices</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-[70px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {locations.map((location) => (
                <TableRow key={location.id}>
                  <TableCell className="font-medium">{location.name}</TableCell>
                  <TableCell>
                    <div className="max-w-[200px] truncate">
                      {location.description || (
                        <span className="text-muted-foreground">
                          No description
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {location.external_endpoint ? (
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {location.external_endpoint}
                      </code>
                    ) : (
                      <Badge variant="outline">None</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">
                        {location.device_count}
                      </span>
                      <span className="text-muted-foreground text-sm">
                        devices
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm text-muted-foreground">
                      {new Date(location.created_at).toLocaleDateString()}
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
                        <DropdownMenuItem
                          onClick={() => openEditModal(location)}
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => openDeleteDialog(location)}
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
        )}
      </CardContent>

      {/* Edit Modal */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Location</DialogTitle>
            <DialogDescription>
              Update the location configuration.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <FormErrorSummary messages={Object.values(formErrors)} />
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Name *</Label>
              <Input
                id="edit-name"
                ref={editNameRef}
                value={formData.name || ''}
                onChange={(e) =>
                  updateField('name', e.target.value)
                }
                placeholder="Enter location name"
                disabled={isSubmitting}
              />
              {renderFieldError('name')}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description || ''}
                onChange={(e) =>
                  updateField('description', e.target.value)
                }
                placeholder="Enter location description"
                rows={3}
                disabled={isSubmitting}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-external_endpoint">External Endpoint</Label>
              <Input
                id="edit-external_endpoint"
                ref={editExternalEndpointRef}
                value={formData.external_endpoint || ''}
                onChange={(e) =>
                  updateField('external_endpoint', e.target.value)
                }
                placeholder="vpn.example.com"
                disabled={isSubmitting}
              />
              <p className="text-xs text-muted-foreground">
                Hostname or IP address (no port)
              </p>
              {renderFieldError('external_endpoint')}
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
            </div>
            <div className="col-span-2">
              <InterfacePropertiesForm
                value={formData.interface_properties}
                onChange={(properties) =>
                  updateField('interface_properties', properties)
                }
                disabled={isSubmitting}
                level="location"
              />
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
              onClick={handleUpdateLocation}
              loading={isSubmitting}
              loadingText="Updating..."
            >
              Update Location
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Location</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{selectedLocation?.name}
              &rdquo;? This action cannot be undone and will affect any devices
              assigned to this location.
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
              onClick={handleDeleteLocation}
              loading={isSubmitting}
              loadingText="Deleting..."
            >
              Delete Location
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
