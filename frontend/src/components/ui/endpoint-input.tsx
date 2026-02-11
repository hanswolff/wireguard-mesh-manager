import type { InputHTMLAttributes } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface EndpointInputProps {
  label: string;
  hostId: string;
  portId: string;
  hostLabel?: string;
  portLabel?: string;
  hostPlaceholder?: string;
  portPlaceholder?: string;
  hostError?: string;
  portError?: string;
  hostProps: InputHTMLAttributes<HTMLInputElement>;
  portProps: InputHTMLAttributes<HTMLInputElement>;
  disabled?: boolean;
  helperText?: string;
}

export function EndpointInput({
  label,
  hostId,
  portId,
  hostLabel = 'Host / IP',
  portLabel = 'Port',
  hostPlaceholder,
  portPlaceholder,
  hostError,
  portError,
  hostProps,
  portProps,
  disabled,
  helperText,
}: EndpointInputProps) {
  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor={hostId} className="text-xs text-muted-foreground">
            {hostLabel}
          </Label>
          <Input
            id={hostId}
            {...hostProps}
            placeholder={hostPlaceholder}
            disabled={disabled}
          />
          <p
            className="min-h-[1.25rem] text-sm text-destructive"
            {...(hostError ? { role: 'alert' } : { 'aria-hidden': true })}
          >
            {hostError ?? ''}
          </p>
        </div>
        <div className="grid gap-2">
          <Label htmlFor={portId} className="text-xs text-muted-foreground">
            {portLabel}
          </Label>
          <Input
            id={portId}
            type="number"
            inputMode="numeric"
            min={1}
            max={65535}
            step={1}
            placeholder={portPlaceholder}
            disabled={disabled}
            {...portProps}
          />
          <p
            className="min-h-[1.25rem] text-sm text-destructive"
            {...(portError ? { role: 'alert' } : { 'aria-hidden': true })}
          >
            {portError ?? ''}
          </p>
        </div>
      </div>
      {helperText && (
        <p className="text-xs text-muted-foreground">{helperText}</p>
      )}
    </div>
  );
}
