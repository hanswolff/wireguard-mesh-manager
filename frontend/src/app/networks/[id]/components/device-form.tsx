'use client';

import { type FieldErrors, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { LoadingButton } from '@/components/ui/loading-button';
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
import { SecureTextarea } from '@/components/ui/secure-textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { InterfacePropertiesForm } from '@/components/ui/interface-properties-form';
import { FormErrorSummary } from '@/components/ui/form-error-summary';
import {
  type DeviceCreate,
  type DeviceResponse,
  type DeviceUpdate,
  type LocationResponse,
} from '@/lib/api-client';
import apiClient from '@/lib/api-client';
import { ChevronDown, ChevronUp, Key } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';
import { useUnlock } from '@/contexts/unlock-context';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import { isIpInCidr } from '@/lib/utils/cidr';
import { EndpointInput } from '@/components/ui/endpoint-input';

const formatLocationWithNetwork = (
  locationName: string,
  networkName?: string | null
): string => {
  if (!networkName) return locationName;
  return `${locationName} (${networkName})`;
};

interface LocationSelectItemProps {
  location: LocationResponse;
}

const LocationSelectItem = ({ location }: LocationSelectItemProps) => (
  <div className="flex flex-col">
    <span className="font-medium">{location.name}</span>
    <span className="text-xs text-muted-foreground">
      {location.network_name || 'Unknown Network'}
    </span>
  </div>
);

const deviceFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  location_id: z.string().min(1, 'Location is required'),
  description: z.string().optional(),
  wireguard_ip: z
    .string()
    .regex(/^\d+\.\d+\.\d+\.\d+$/, 'Invalid IP address')
    .optional()
    .or(z.literal('')),
  external_endpoint_host: z.string().max(255).optional(),
  external_endpoint_port: z.number().int().min(1).max(65535).optional(),
  internal_endpoint_host: z.string().max(255).optional(),
  internal_endpoint_port: z.number().int().min(1).max(65535).optional(),
  public_key: z
    .string()
    .min(44, 'Public key must be 44 characters')
    .max(44, 'Public key must be 44 characters'),
  private_key: z
    .string()
    .min(44, 'Private key must be 44-56 characters')
    .max(56, 'Private key must be 44-56 characters')
    .optional()
    .or(z.literal('')),
  preshared_key: z
    .string()
    .min(44, 'PSK must be 44 characters')
    .max(44, 'PSK must be 44 characters')
    .optional()
    .or(z.literal('')),
  enabled: z.boolean(),
  interface_properties: z.record(z.string(), z.unknown()).optional().nullable(),
}).superRefine((data, ctx) => {
  if (data.external_endpoint_host && !data.external_endpoint_port) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Port is required when an external host is set',
      path: ['external_endpoint_port'],
    });
  }

  const internalHost = data.internal_endpoint_host;
  const internalPort = data.internal_endpoint_port;
  if ((internalHost && !internalPort) || (!internalHost && internalPort)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Internal endpoint requires both host and port',
      path: internalHost ? ['internal_endpoint_port'] : ['internal_endpoint_host'],
    });
  }

  // Require at least one port to be provided (internal or external)
  const hasExternalPort = data.external_endpoint_port !== undefined && data.external_endpoint_port !== null;
  const hasInternalPort = data.internal_endpoint_port !== undefined && data.internal_endpoint_port !== null;

  if (!hasExternalPort && !hasInternalPort) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'At least one port (internal or external) must be provided',
      path: ['external_endpoint_port'],
    });
  }
});

type DeviceFormData = z.infer<typeof deviceFormSchema>;

interface DeviceFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: DeviceCreate | DeviceUpdate) => Promise<void>;
  isSubmitting: boolean;
  device?: DeviceResponse | null;
  locations: LocationResponse[];
  networkId: string;
  networkCidr?: string | null;
  mode: 'create' | 'edit';
  preselectedNetworkId?: string;
  preselectedLocationId?: string;
}

export default function DeviceForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  device,
  locations,
  networkId,
  networkCidr,
  mode,
  preselectedNetworkId,
  preselectedLocationId,
}: DeviceFormProps) {
  const { requireUnlock } = useUnlock();
  const [isGeneratingKeys, setIsGeneratingKeys] = useState(false);
  const [isGeneratingPresharedKey, setIsGeneratingPresharedKey] = useState(false);
  const [generatedPrivateKey, setGeneratedPrivateKey] = useState(false);
  const [isLoadingPrivateKey, setIsLoadingPrivateKey] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [pendingPrivateKeyLoad, setPendingPrivateKeyLoad] = useState(false);
  const [showPrivateKeyField, setShowPrivateKeyField] = useState(
    mode === 'create'
  );
  const [wireguardIpPlaceholder, setWireguardIpPlaceholder] = useState('10.0.0.2');
  const [externalEndpointHostPlaceholder, setExternalEndpointHostPlaceholder] =
    useState('example.com');
  const externalEndpointPortPlaceholder = '51820';
  const locationTriggerRef = useRef<HTMLButtonElement | null>(null);
  const errorLineClass = 'min-h-[1.25rem] text-sm text-destructive';

  const form = useForm<DeviceFormData>({
    resolver: zodResolver(deviceFormSchema),
    shouldFocusError: false,
    defaultValues: {
      name: device?.name || '',
      location_id:
        device?.location_id ||
        (mode === 'create' && preselectedLocationId) ||
        '',
      description: device?.description || '',
      wireguard_ip: device?.wireguard_ip || '',
      external_endpoint_host: device?.external_endpoint_host ?? undefined,
      external_endpoint_port: device?.external_endpoint_port ?? undefined,
      internal_endpoint_host: device?.internal_endpoint_host ?? undefined,
      internal_endpoint_port: device?.internal_endpoint_port ?? undefined,
      public_key: device?.public_key || '',
      private_key: '',
      preshared_key: '',
      enabled: device?.enabled ?? true,
      interface_properties: device?.interface_properties || null,
    },
  });

  const errorMessages = useMemo(() => {
    return Object.values(form.formState.errors)
      .map((error) => error?.message)
      .filter((message): message is string => Boolean(message));
  }, [form.formState.errors]);

  const setPrivateKeyVisible = useCallback(() => {
    setShowPrivateKeyField(true);
  }, []);

  const focusFirstErrorField = useCallback(
    (hasError: (field: keyof DeviceFormData) => boolean) => {
      const fieldOrder: (keyof DeviceFormData)[] = [
        'name',
        'location_id',
        'description',
        'wireguard_ip',
        'external_endpoint_host',
        'external_endpoint_port',
        'internal_endpoint_host',
        'internal_endpoint_port',
        'public_key',
        'private_key',
        'preshared_key',
      ];

      for (const field of fieldOrder) {
        if (!hasError(field)) continue;
        if (field === 'location_id') {
          locationTriggerRef.current?.focus();
        } else if (field === 'private_key') {
          setPrivateKeyVisible();
          form.setFocus(field);
        } else {
          form.setFocus(field);
        }
        break;
      }
    },
    [form, setPrivateKeyVisible]
  );

  useEffect(() => {
    if (open) {
      setShowPrivateKeyField(mode === 'create');
      // Set placeholder based on network CIDR
      if (networkCidr) {
        const cidrParts = networkCidr.split('/');
        if (cidrParts.length >= 2) {
          const networkAddress = cidrParts[0];
          const octets = networkAddress.split('.');
          if (octets.length === 4) {
            setWireguardIpPlaceholder(`${octets[0]}.${octets[1]}.${octets[2]}.2`);
          }
        }
      }
      // Set preselected location in create mode
      if (mode === 'create' && preselectedLocationId) {
        form.setValue('location_id', preselectedLocationId);
      }
    }
  }, [open, mode, networkCidr, preselectedLocationId, form]);

  // Update form values when device data changes (for edit mode)
  useEffect(() => {
    if (mode === 'edit' && device) {
      form.reset({
        name: device.name || '',
        location_id: device.location_id || '',
        description: device.description || '',
        wireguard_ip: device.wireguard_ip || '',
        external_endpoint_host: device.external_endpoint_host ?? undefined,
        external_endpoint_port: device.external_endpoint_port ?? undefined,
        internal_endpoint_host: device.internal_endpoint_host ?? undefined,
        internal_endpoint_port: device.internal_endpoint_port ?? undefined,
        public_key: device.public_key || '',
        private_key: '',
        preshared_key: '',
        enabled: device.enabled ?? true,
        interface_properties: device.interface_properties || null,
      });
    }
  }, [mode, device, form]);

  // Update placeholder when location changes
  const locationId = form.watch('location_id');
  useEffect(() => {
    if (locationId && networkCidr) {
      const cidrParts = networkCidr.split('/');
      if (cidrParts.length >= 2) {
        const networkAddress = cidrParts[0];
        const octets = networkAddress.split('.');
        if (octets.length === 4) {
          setWireguardIpPlaceholder(`${octets[0]}.${octets[1]}.${octets[2]}.2`);
        }
      }
    }

    // Update external endpoint placeholder based on selected location
    if (locationId) {
      const selectedLocation = locations.find((loc) => loc.id === locationId);
      if (selectedLocation?.external_endpoint) {
        setExternalEndpointHostPlaceholder(selectedLocation.external_endpoint);
      } else {
        setExternalEndpointHostPlaceholder('example.com');
      }
    }
  }, [locationId, networkCidr, form, locations]);

  // Validate wireguard_ip when it changes
  const wireguardIp = form.watch('wireguard_ip');
  useEffect(() => {
    if (wireguardIp && networkCidr && wireguardIp.trim() !== '') {
      // Check if IP is within network CIDR
      if (!isIpInCidr(wireguardIp, networkCidr)) {
        form.setError('wireguard_ip', {
          type: 'manual',
          message: `IP address ${wireguardIp} is not within the network CIDR (${networkCidr})`,
        });
      } else {
        form.clearErrors('wireguard_ip');
      }
    } else if (wireguardIp && wireguardIp.trim() !== '') {
      // Validate IP format
      const ipRegex = /^\d+\.\d+\.\d+\.\d+$/;
      if (!ipRegex.test(wireguardIp)) {
        form.setError('wireguard_ip', {
          type: 'manual',
          message: 'Invalid IP address format',
        });
      }
    } else {
      form.clearErrors('wireguard_ip');
    }
  }, [wireguardIp, networkCidr, form]);

  const handleSubmit = async (data: DeviceFormData) => {
    if (mode === 'create' && !data.private_key) {
      form.setError('private_key', {
        type: 'manual',
        message: 'Private key is required to create a device',
      });
      setPrivateKeyVisible();
      form.setFocus('private_key');
      return;
    }

    // Validate WireGuard IP is within network CIDR
    if (data.wireguard_ip && networkCidr && data.wireguard_ip.trim() !== '') {
      if (!isIpInCidr(data.wireguard_ip, networkCidr)) {
        form.setError('wireguard_ip', {
          type: 'manual',
          message: `IP address ${data.wireguard_ip} is not within network CIDR (${networkCidr})`,
        });
        form.setFocus('wireguard_ip');
        return;
      }
    }

    try {
      if (mode === 'create') {
        const privateKey = data.private_key ?? '';
        const submitData: DeviceCreate = {
          ...data,
          network_id: preselectedNetworkId || networkId,
          private_key: privateKey,
          preshared_key: data.preshared_key || undefined,
          wireguard_ip: data.wireguard_ip || undefined,
          external_endpoint_host: data.external_endpoint_host || undefined,
          external_endpoint_port: data.external_endpoint_port ?? undefined,
          internal_endpoint_host: data.internal_endpoint_host || undefined,
          internal_endpoint_port: data.internal_endpoint_port ?? undefined,
        };
        await onSubmit(submitData);
        // Reset form on success (parent handles dialog closing)
        form.reset();
        setGeneratedPrivateKey(false);
      } else {
        const submitData: DeviceUpdate = {
          ...data,
          private_key: data.private_key || undefined,
          preshared_key: data.preshared_key || undefined,
          wireguard_ip: data.wireguard_ip || undefined,
          external_endpoint_host: data.external_endpoint_host || undefined,
          external_endpoint_port: data.external_endpoint_port ?? undefined,
          internal_endpoint_host: data.internal_endpoint_host || undefined,
          internal_endpoint_port: data.internal_endpoint_port ?? undefined,
        };
        await onSubmit(submitData);
      }
    } catch (err) {
      // Handle 422 validation errors from backend
      if (err && typeof err === 'object' && 'fieldErrors' in err) {
        const fieldErrors = (err as { fieldErrors?: Record<string, string> }).fieldErrors;
        if (fieldErrors) {
          Object.entries(fieldErrors).forEach(([field, message]) => {
            form.setError(field as keyof DeviceFormData, {
              type: 'manual',
              message,
            });
          });
          focusFirstErrorField(
            (field) => Boolean(fieldErrors[field as keyof typeof fieldErrors])
          );
        }
      }

      // Re-throw the error so parent can handle it (e.g., show toast)
      throw err;
    }
  };

  const handleGenerateKeys = async () => {
    setIsGeneratingKeys(true);
    try {
      // Try CLI method first
      let response;
      try {
        response = await apiClient.generateWireGuardKeys({ method: 'cli' });
      } catch (cliError) {
        // If CLI method fails, try crypto method
        console.warn('CLI key generation failed, falling back to crypto method', cliError);
        response = await apiClient.generateWireGuardKeys({ method: 'crypto' });
      }

      setGeneratedPrivateKey(true);
      form.setValue('public_key', response.public_key);
      form.setValue('private_key', response.private_key);
      toast({
        title: 'Keys Generated',
        description: `New WireGuard key pair generated using ${response.method === 'cli' ? 'CLI tools' : 'crypto library'} method`,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to generate keys';
      toast({
        title: 'Key Generation Failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsGeneratingKeys(false);
    }
  };

  const handleGeneratePresharedKey = async () => {
    try {
      setIsGeneratingPresharedKey(true);
      const response = await apiClient.generateWireGuardPresharedKey();
      form.setValue('preshared_key', response.preshared_key);
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

  const extractPrivateKey = useCallback((configResponse: unknown) => {
    if (!configResponse || typeof configResponse !== 'object') {
      return null;
    }

    const response = configResponse as {
      configuration?: { interface?: { private_key?: string } };
      config?: string;
    };

    if (response.configuration?.interface?.private_key) {
      return response.configuration.interface.private_key;
    }

    if (response.config && typeof response.config === 'string') {
      try {
        const parsed = JSON.parse(response.config) as {
          interface?: { private_key?: string };
        };
        return parsed.interface?.private_key || null;
      } catch {
        return null;
      }
    }

    return null;
  }, []);

  const loadPrivateKey = useCallback(async () => {
    if (!device) return;
    setIsLoadingPrivateKey(true);
    try {
      const response = await apiClient.getAdminDeviceConfig(device.id, {
        format: 'json',
      });
      const privateKey = extractPrivateKey(response);
      if (!privateKey) {
        toast({
          title: 'Private Key Unavailable',
          description: 'Unable to load the private key for this device.',
          variant: 'destructive',
        });
        return;
      }

      form.setValue('private_key', privateKey, { shouldDirty: true });
      toast({
        title: 'Private Key Loaded',
        description: 'Private key has been loaded into the form.',
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to load private key';
      toast({
        title: 'Private Key Load Failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsLoadingPrivateKey(false);
    }
  }, [device, extractPrivateKey, form]);

  const handleLoadPrivateKey = useCallback(() => {
    const unlocked = requireUnlock(() => {
      void loadPrivateKey();
    });

    if (!unlocked) {
      setPendingPrivateKeyLoad(true);
      setShowUnlockModal(true);
    }
  }, [requireUnlock, loadPrivateKey]);

  const handleUnlockSuccess = useCallback(() => {
    setShowUnlockModal(false);
    if (pendingPrivateKeyLoad) {
      setPendingPrivateKeyLoad(false);
      void loadPrivateKey();
    }
  }, [pendingPrivateKeyLoad, loadPrivateKey]);

  const title = mode === 'create' ? 'Add New Device' : 'Edit Device';
  const description =
    mode === 'create'
      ? 'Add a new device to this network.'
      : 'Update the device configuration.';
  const isEditMode = mode === 'edit';
  const handleInvalidSubmit = useCallback(
    (errors: FieldErrors<DeviceFormData>) => {
      if (errors.private_key) {
        setPrivateKeyVisible();
      }
      focusFirstErrorField((field) => Boolean(errors[field]));
    },
    [focusFirstErrorField, setPrivateKeyVisible]
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(handleSubmit, handleInvalidSubmit)}>
          <div className="grid gap-4 py-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <FormErrorSummary messages={errorMessages} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                {...form.register('name')}
                placeholder="Enter device name"
                disabled={isSubmitting}
              />
              <p
                className={errorLineClass}
                {...(form.formState.errors.name
                  ? { role: 'alert' }
                  : { 'aria-hidden': true })}
              >
                {form.formState.errors.name?.message ?? ''}
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="location_id">Location *</Label>
              <Select
                value={form.watch('location_id')}
                onValueChange={(value) => form.setValue('location_id', value)}
                disabled={isSubmitting}
              >
                <SelectTrigger ref={locationTriggerRef}>
                  <SelectValue
                    placeholder={
                      mode === 'edit' && device?.location_name
                        ? formatLocationWithNetwork(
                            device.location_name,
                            device.network_name
                          )
                        : 'Select a location'
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {locations.map((location) => (
                    <SelectItem key={location.id} value={location.id}>
                      <LocationSelectItem location={location} />
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p
                className={errorLineClass}
                {...(form.formState.errors.location_id
                  ? { role: 'alert' }
                  : { 'aria-hidden': true })}
              >
                {form.formState.errors.location_id?.message ?? ''}
              </p>
            </div>

            <div className="grid gap-2 md:col-span-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                {...form.register('description')}
                placeholder="Enter device description"
                rows={3}
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="wireguard_ip">WireGuard IP</Label>
              <Input
                id="wireguard_ip"
                {...form.register('wireguard_ip')}
                placeholder={wireguardIpPlaceholder}
                disabled={isSubmitting}
              />
              <p
                className={errorLineClass}
                {...(form.formState.errors.wireguard_ip
                  ? { role: 'alert' }
                  : { 'aria-hidden': true })}
              >
                {form.formState.errors.wireguard_ip?.message ?? ''}
              </p>
              {networkCidr && (
                <p className="text-xs text-muted-foreground">
                  Network CIDR: {networkCidr}
                </p>
              )}
            </div>

            <div className="grid gap-2 md:col-span-2">
              <EndpointInput
                label="External Endpoint"
                hostId="external_endpoint_host"
                portId="external_endpoint_port"
                hostPlaceholder={externalEndpointHostPlaceholder}
                portPlaceholder={externalEndpointPortPlaceholder}
                hostProps={form.register('external_endpoint_host')}
                portProps={form.register('external_endpoint_port', {
                  setValueAs: (value) => {
                    if (value === '' || value === null || value === undefined) {
                      return undefined;
                    }
                    const parsed = Number(value);
                    return Number.isNaN(parsed) ? undefined : parsed;
                  },
                })}
                hostError={form.formState.errors.external_endpoint_host?.message}
                portError={form.formState.errors.external_endpoint_port?.message}
                disabled={isSubmitting}
                helperText="Leave host empty to inherit the location host."
              />
            </div>

            <div className="grid gap-2 md:col-span-2">
              <EndpointInput
                label="Internal Endpoint"
                hostId="internal_endpoint_host"
                portId="internal_endpoint_port"
                hostPlaceholder="192.168.1.100"
                portPlaceholder={externalEndpointPortPlaceholder}
                hostProps={form.register('internal_endpoint_host')}
                portProps={form.register('internal_endpoint_port', {
                  setValueAs: (value) => {
                    if (value === '' || value === null || value === undefined) {
                      return undefined;
                    }
                    const parsed = Number(value);
                    return Number.isNaN(parsed) ? undefined : parsed;
                  },
                })}
                hostError={form.formState.errors.internal_endpoint_host?.message}
                portError={form.formState.errors.internal_endpoint_port?.message}
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-2 md:col-span-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="public_key">Public Key *</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleGenerateKeys}
                  disabled={isSubmitting || isGeneratingKeys}
                  className="gap-2"
                >
                  <Key className="h-4 w-4" />
                  {isGeneratingKeys ? 'Generating...' : 'Generate Keys'}
                </Button>
              </div>
              <Textarea
                id="public_key"
                {...form.register('public_key', {
                  setValueAs: (value) => value.trim(),
                })}
                placeholder="Enter device public key or click Generate Keys"
                rows={3}
                disabled={isSubmitting}
              />
              <p
                className={errorLineClass}
                {...(form.formState.errors.public_key
                  ? { role: 'alert' }
                  : { 'aria-hidden': true })}
              >
                {form.formState.errors.public_key?.message ?? ''}
              </p>
            </div>

            <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950 md:col-span-2">
              <button
                type="button"
                onClick={() => setShowPrivateKeyField((prev) => !prev)}
                disabled={isSubmitting}
                aria-expanded={showPrivateKeyField}
                className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-medium"
              >
                <span>Private Key {mode === 'create' ? '*' : ''}</span>
                {showPrivateKeyField ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>
              {showPrivateKeyField && (
                <div className="space-y-4 border-t border-blue-200 px-4 pb-4 pt-3 dark:border-blue-800">
                  {isEditMode && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleLoadPrivateKey}
                      disabled={isSubmitting || isLoadingPrivateKey}
                    >
                      {isLoadingPrivateKey ? 'Loading...' : 'Load Private Key'}
                    </Button>
                  )}
                  <SecureTextarea
                    id="private_key"
                    {...form.register('private_key', {
                      setValueAs: (value) => value.trim(),
                    })}
                    placeholder="Private key will be stored encrypted after saving"
                    rows={3}
                    disabled={isSubmitting}
                  />
                  <p
                    className={errorLineClass}
                    {...(form.formState.errors.private_key
                      ? { role: 'alert' }
                      : { 'aria-hidden': true })}
                  >
                    {form.formState.errors.private_key?.message ?? ''}
                  </p>
                  <div className="text-sm text-muted-foreground">
                    {isEditMode
                      ? 'Load the current private key or paste a new one. Updates are stored encrypted on save.'
                      : generatedPrivateKey
                        ? 'This private key was generated for you and will be stored encrypted when you save the device.'
                        : 'Paste or generate a private key. It will be stored encrypted when you save the device.'}
                  </div>
                </div>
              )}
            </div>

            <div className="grid gap-2 md:col-span-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="preshared_key">Preshared Key (Optional)</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleGeneratePresharedKey}
                  disabled={isSubmitting || isGeneratingPresharedKey}
                  className="gap-2"
                >
                  <Key className="h-4 w-4" />
                  {isGeneratingPresharedKey ? 'Generating...' : 'Generate'}
                </Button>
              </div>
              <Textarea
                id="preshared_key"
                {...form.register('preshared_key', {
                  setValueAs: (value) => value.trim(),
                })}
                placeholder="Enter preshared key for additional security"
                rows={3}
                disabled={isSubmitting}
              />
              <p
                className={errorLineClass}
                {...(form.formState.errors.preshared_key
                  ? { role: 'alert' }
                  : { 'aria-hidden': true })}
              >
                {form.formState.errors.preshared_key?.message ?? ''}
              </p>
            </div>

            <div className="flex items-center space-x-2 md:col-span-2">
              <Switch
                id="enabled"
                checked={form.watch('enabled')}
                onCheckedChange={(checked) => form.setValue('enabled', checked)}
                disabled={isSubmitting}
              />
              <Label htmlFor="enabled">Enabled</Label>
            </div>

            <div className="md:col-span-2">
              <InterfacePropertiesForm
                key={device?.id}
                value={form.watch('interface_properties')}
                onChange={(properties) =>
                  form.setValue('interface_properties', properties)
                }
                disabled={isSubmitting}
                level="device"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <LoadingButton
              type="submit"
              loading={isSubmitting}
              loadingText={mode === 'create' ? 'Creating...' : 'Updating...'}
            >
              {mode === 'create' ? 'Add Device' : 'Update Device'}
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
      {showUnlockModal && (
        <MasterPasswordUnlockModal
          isOpen={showUnlockModal}
          onClose={() => {
            setShowUnlockModal(false);
            setPendingPrivateKeyLoad(false);
          }}
          onSuccess={handleUnlockSuccess}
          title="Unlock to Load Private Key"
          description="Enter the master password to decrypt and load the private key."
        />
      )}
    </Dialog>
  );
}
