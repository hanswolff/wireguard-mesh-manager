import { useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { InterfacePropertiesForm } from '@/components/ui/interface-properties-form';
import { FormErrorSummary } from '@/components/ui/form-error-summary';
import {
  WireGuardNetworkCreate,
  WireGuardNetworkUpdate,
  WireGuardNetworkResponse,
} from '@/lib/api-client';

interface NetworkFormProps {
  data?: Partial<WireGuardNetworkResponse>;
  onSubmit: (data: WireGuardNetworkCreate | WireGuardNetworkUpdate) => void;
  isSubmitting?: boolean;
  submitText?: string;
  formErrors?: Record<string, string>;
}

const formValidationRules = {
  name: { required: 'Name is required' },
  network_cidr: { required: 'Network CIDR is required' },
};

export function NetworkForm({
  data,
  onSubmit,
  isSubmitting = false,
  submitText = 'Save',
  formErrors,
}: NetworkFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<WireGuardNetworkCreate>({
    defaultValues: {
      name: data?.name || '',
      description: data?.description || '',
      network_cidr: data?.network_cidr || '',
      dns_servers: data?.dns_servers || '',
      mtu: data?.mtu,
      persistent_keepalive: data?.persistent_keepalive,
      interface_properties: data?.interface_properties || null,
    },
  });

  const interfaceProperties = watch('interface_properties');
  const allErrors = Object.values(errors)
    .map((error) => error?.message)
    .filter((message): message is string => Boolean(message));

  const backendErrorMessages = formErrors
    ? Object.values(formErrors).filter(
        (message): message is string => Boolean(message)
      )
    : [];

  const errorMessages = [...allErrors, ...backendErrorMessages];

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 py-4">
      <FormErrorSummary messages={errorMessages} />
      <div className="grid gap-2">
        <Label htmlFor="name">Name *</Label>
        <Input
          id="name"
          {...register('name', formValidationRules.name)}
          placeholder="Enter network name"
          disabled={isSubmitting}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          {...register('description')}
          placeholder="Enter network description"
          rows={3}
          disabled={isSubmitting}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="network_cidr">Network CIDR *</Label>
        <Input
          id="network_cidr"
          {...register('network_cidr', formValidationRules.network_cidr)}
          placeholder="10.0.0.0/24"
          disabled={isSubmitting}
        />
        {errors.network_cidr && (
          <p className="text-sm text-destructive">
            {errors.network_cidr.message}
          </p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="dns_servers">DNS Servers</Label>
        <Input
          id="dns_servers"
          {...register('dns_servers')}
          placeholder="1.1.1.1, 8.8.8.8"
          disabled={isSubmitting}
        />
      </div>

      <div className="col-span-2">
        <InterfacePropertiesForm
          value={interfaceProperties}
          onChange={(properties) =>
            setValue('interface_properties', properties)
          }
          disabled={isSubmitting}
          level="network"
        />
      </div>

      <Button type="submit" disabled={isSubmitting} className="hidden">
        {submitText}
      </Button>
    </form>
  );
}
