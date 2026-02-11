'use client';

import * as React from 'react';
import { useFormContext } from 'react-hook-form';

import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  cidrSchema,
  endpointSchema,
  ipAddressSchema,
  ipAllowlistSchema,
} from '@/lib/validation-schemas';

// CIDR Input Component
interface CidrInputProps {
  name: string;
  label?: string;
  description?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
}

export function CidrInput({
  name,
  label,
  description,
  placeholder = '192.168.1.0/24',
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  required = false,
  className,
}: CidrInputProps) {
  return (
    <FormField
      name={name}
      render={({ field }) => (
        <FormItem className={className}>
          {label && <FormLabel>{label}</FormLabel>}
          <FormControl>
            <Input
              {...field}
              placeholder={placeholder}
              className={cn(
                'font-mono',
                field.value &&
                  !cidrSchema.safeParse(field.value).success &&
                  'border-destructive'
              )}
            />
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// Endpoint Input Component
interface EndpointInputProps {
  name: string;
  label?: string;
  description?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
}

export function EndpointInput({
  name,
  label,
  description,
  placeholder = 'example.com:51820',
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  required = false,
  className,
}: EndpointInputProps) {
  return (
    <FormField
      name={name}
      render={({ field }) => (
        <FormItem className={className}>
          {label && <FormLabel>{label}</FormLabel>}
          <FormControl>
            <Input
              {...field}
              placeholder={placeholder}
              className={cn(
                'font-mono',
                field.value &&
                  !endpointSchema.safeParse(field.value).success &&
                  'border-destructive'
              )}
            />
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// IP Address Input Component
interface IpAddressInputProps {
  name: string;
  label?: string;
  description?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
}

export function IpAddressInput({
  name,
  label,
  description,
  placeholder = '192.168.1.1',
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  required = false,
  className,
}: IpAddressInputProps) {
  return (
    <FormField
      name={name}
      render={({ field }) => (
        <FormItem className={className}>
          {label && <FormLabel>{label}</FormLabel>}
          <FormControl>
            <Input
              {...field}
              placeholder={placeholder}
              className={cn(
                'font-mono',
                field.value &&
                  !ipAddressSchema.safeParse(field.value).success &&
                  'border-destructive'
              )}
            />
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// IP Allowlist Input Component (supports multiple entries)
interface IpAllowlistInputProps {
  name: string;
  label?: string;
  description?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
  onAddEntry?: (value: string) => void;
  onRemoveEntry?: (index: number) => void;
}

export function IpAllowlistInput({
  name,
  label,
  description,
  placeholder = '192.168.1.0/24',
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  required = false,
  className,
}: IpAllowlistInputProps) {
  const [newValue, setNewValue] = React.useState('');
  const {
    setValue,
    watch,
    formState: { errors },
  } = useFormContext();
  const entries = watch(name) || [];

  const addEntry = () => {
    if (newValue && ipAllowlistSchema.safeParse(newValue).success) {
      const updatedEntries = [...entries, newValue];
      setValue(name, updatedEntries, { shouldValidate: true });
      setNewValue('');
    }
  };

  const removeEntry = (index: number) => {
    const updatedEntries = entries.filter(
      (_: string, i: number) => i !== index
    );
    setValue(name, updatedEntries, { shouldValidate: true });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addEntry();
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const fieldError = errors[name];

  return (
    <FormField
      name={name}
      render={() => (
        <FormItem className={className}>
          {label && <FormLabel>{label}</FormLabel>}
          <FormControl>
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder={placeholder}
                  aria-label={label || 'IP Allowlist entry'}
                  className={cn(
                    'font-mono flex-1',
                    newValue &&
                      !ipAllowlistSchema.safeParse(newValue).success &&
                      'border-destructive'
                  )}
                  onKeyDown={handleKeyDown}
                />
                <button
                  type="button"
                  onClick={addEntry}
                  disabled={
                    !newValue || !ipAllowlistSchema.safeParse(newValue).success
                  }
                  className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
              </div>
              {entries.length > 0 && (
                <div className="space-y-1">
                  {entries.map((entry: string, index: number) => (
                    <div
                      key={index}
                      className="flex items-center justify-between bg-muted/50 px-2 py-1 rounded text-sm font-mono"
                    >
                      <span>{entry}</span>
                      <button
                        type="button"
                        onClick={() => removeEntry(index)}
                        className="text-destructive hover:text-destructive/90 ml-2"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
