'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Save,
  AlertTriangle,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LoadingButton } from '@/components/ui/loading-button';
import { toast } from '@/components/ui/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  type WireGuardNetworkResponse,
  type WireGuardNetworkUpdate,
} from '@/lib/api-client';
import apiClient from '@/lib/api-client';
import { FormErrorSummary } from '@/components/ui/form-error-summary';

export default function NetworkEditPage() {
  const params = useParams();
  const router = useRouter();
  const [network, setNetwork] = useState<WireGuardNetworkResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeneratingPresharedKey, setIsGeneratingPresharedKey] =
    useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const cidrPattern = /^\d+\.\d+\.\d+\.\d+\/\d+$/;

  const [formData, setFormData] = useState<WireGuardNetworkUpdate>({
    name: '',
    description: '',
    network_cidr: '',
    dns_servers: '',
    preshared_key: '',
  });

  const networkId = params.id as string;

  const fetchNetwork = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getNetwork(networkId);
      setNetwork(data);

      setFormData({
        name: data.name,
        description: data.description || '',
        network_cidr: data.network_cidr,
        dns_servers: data.dns_servers || '',
        preshared_key: '',
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to fetch network data'
      );
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to fetch network data',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [networkId]);

  useEffect(() => {
    void fetchNetwork();
  }, [networkId, fetchNetwork]);

  const updateField = <K extends keyof WireGuardNetworkUpdate>(
    field: K,
    value: WireGuardNetworkUpdate[K]
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

  const renderFieldError = (field: keyof WireGuardNetworkUpdate) => {
    const message = formErrors[field as string];
    if (!message) {
      return null;
    }
    return <p className="text-xs text-destructive">{message}</p>;
  };

  const formErrorMessages = Object.values(formErrors);

  const validateFormData = (data: Partial<WireGuardNetworkUpdate>) => {
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

  const handleSubmit = async (data: WireGuardNetworkUpdate) => {
    const payload: WireGuardNetworkUpdate = {
      ...data,
      preshared_key: data.preshared_key?.trim() || undefined,
    };
    const validationErrors = validateFormData(payload);

    if (Object.keys(validationErrors).length > 0) {
      setFormErrors(validationErrors);
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
      
      await apiClient.updateNetwork(networkId, payload);

      toast({
        title: 'Network Updated',
        description: `${payload.name} has been updated successfully`,
      });

      router.push(`/networks/${networkId}`);
    } catch (err) {
      const fieldErrors = (err as { fieldErrors?: Record<string, string> })
        .fieldErrors;
      if (fieldErrors && Object.keys(fieldErrors).length > 0) {
        setFormErrors(fieldErrors);
      }
      toast({
        title: 'Update Failed',
        description: err instanceof Error ? err.message : 'Failed to update network',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
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
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
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

  if (error || !network) {
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
            <AlertDescription>{error || 'Network not found'}</AlertDescription>
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
            <Button variant="ghost" onClick={() => router.push(`/networks/${networkId}`)}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Network
            </Button>
            <div className="flex items-center space-x-3">
              <Globe className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-3xl font-bold">Edit Network</h1>
                <p className="text-muted-foreground">
                  {network.name}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="rounded-lg border bg-card p-6 space-y-6">
          <FormErrorSummary messages={formErrorMessages} />
          <div className="grid gap-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
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
              value={formData.dns_servers ?? ''}
              onChange={(e) => updateField('dns_servers', e.target.value)}
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
              value={formData.preshared_key ?? ''}
              onChange={(e) => updateField('preshared_key', e.target.value.trim())}
              placeholder="Paste a WireGuard preshared key"
              rows={3}
              disabled={isSubmitting}
            />
            {renderFieldError('preshared_key')}
            <p className="text-xs text-muted-foreground">
              Default preshared key for locations and devices in this network.
            </p>
          </div>
          <div className="flex justify-end space-x-2">
            <Button
              variant="outline"
              onClick={() => router.back()}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <LoadingButton
              onClick={() => handleSubmit(formData)}
              loading={isSubmitting}
              loadingText="Updating..."
            >
              <Save className="h-4 w-4 mr-2" />
              Update Network
            </LoadingButton>
          </div>
        </div>
      </div>
    </div>
  );
}
