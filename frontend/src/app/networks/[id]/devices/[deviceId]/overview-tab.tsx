import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { type DeviceResponse } from '@/lib/api-client';

interface OverviewTabProps {
  device: DeviceResponse;
}

export function OverviewTab({ device }: OverviewTabProps) {
  const formatEndpoint = (
    host?: string | null,
    port?: number | null,
    locationFallbackHost?: string | null,
    fallbackLabel: string = 'Location host'
  ) => {
    if (host && port) {
      return `${host}:${port}`;
    }
    if (!host && port) {
      // Use location's external endpoint as fallback if available
      if (locationFallbackHost) {
        return `${locationFallbackHost}:${port}`;
      }
      return `${fallbackLabel}:${port}`;
    }
    return 'Not configured';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Device Information</CardTitle>
        <CardDescription>
          Detailed information about this WireGuard device
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <DeviceField label="Device Name" value={device.name} />
          <div>
            <FieldLabel>Status</FieldLabel>
            <Badge variant={device.enabled ? 'default' : 'secondary'}>
              {device.enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
          <DeviceField
            label="Network"
            value={device.network_name || 'Unknown Network'}
          />
          <DeviceField
            label="Location"
            value={device.location_name || 'Unknown Location'}
          />
          <div>
            <FieldLabel>WireGuard IP</FieldLabel>
            <code className="text-sm bg-muted px-2 py-1 rounded">
              {device.wireguard_ip || 'Not assigned'}
            </code>
          </div>
          <div>
            <FieldLabel>External Endpoint</FieldLabel>
            <code className="text-sm bg-muted px-2 py-1 rounded">
              {formatEndpoint(
                device.external_endpoint_host,
                device.external_endpoint_port,
                device.location_external_endpoint
              )}
            </code>
          </div>
          <div>
            <FieldLabel>Internal Endpoint</FieldLabel>
            <code className="text-sm bg-muted px-2 py-1 rounded">
              {formatEndpoint(
                device.internal_endpoint_host,
                device.internal_endpoint_port,
                'Internal host'
              )}
            </code>
          </div>
          <div>
            <FieldLabel>Public Key</FieldLabel>
            <code className="text-xs bg-muted px-2 py-1 rounded block break-all">
              {device.public_key}
            </code>
          </div>
        </div>
        {device.description && (
          <>
            <Separator />
            <div>
              <FieldLabel>Description</FieldLabel>
              <p className="text-sm">{device.description}</p>
            </div>
          </>
        )}
        <Separator />
        <div className="grid gap-4 md:grid-cols-2">
          <DeviceField
            label="Created"
            value={new Date(device.created_at).toLocaleString()}
          />
          <DeviceField
            label="Last Updated"
            value={new Date(device.updated_at).toLocaleString()}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function DeviceField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <p className="text-sm">{value}</p>
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-sm font-medium text-muted-foreground mb-1">
      {children}
    </h4>
  );
}
