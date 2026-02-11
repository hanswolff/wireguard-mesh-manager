import { Copy, Download, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { type DeviceResponse } from '@/lib/api-client';
import { useCopyToClipboard } from './use-copy-to-clipboard';

interface NetworkConfigTabProps {
  device: DeviceResponse;
  onDownloadConfig: () => void;
}

export function NetworkConfigTab({
  device,
  onDownloadConfig,
}: NetworkConfigTabProps) {
  const { copyToClipboard } = useCopyToClipboard();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Network Configuration</CardTitle>
        <CardDescription>
          WireGuard network configuration details for this device
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-1">
          <CopyableField
            label="Public Key"
            value={device.public_key}
            isCode={true}
            onCopy={() => copyToClipboard(device.public_key, 'Public Key')}
          />
          {device.wireguard_ip && (
            <CopyableField
              label="WireGuard IP Address"
              value={device.wireguard_ip}
              onCopy={() =>
                copyToClipboard(device.wireguard_ip!, 'WireGuard IP')
              }
            />
          )}
        </div>

        <Separator />

        <div className="flex items-center space-x-2">
          <Button onClick={onDownloadConfig}>
            <Download className="h-4 w-4 mr-2" />
            Download Configuration File
          </Button>
        </div>

        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            The configuration file contains all the necessary WireGuard settings
            for this device to connect to the network. Keep this file secure and
            only share it with authorized users of this device.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}

function CopyableField({
  label,
  value,
  isCode = false,
  onCopy,
}: {
  label: string;
  value: string;
  isCode?: boolean;
  onCopy: () => void;
}) {
  const CodeComponent = isCode ? 'code' : 'span';
  const codeClass = isCode
    ? 'text-xs bg-muted px-2 py-1 rounded flex-1 break-all'
    : 'text-sm bg-muted px-2 py-1 rounded flex-1 break-all';

  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div className="flex items-center space-x-2">
        <CodeComponent className={codeClass}>{value}</CodeComponent>
        <Button variant="outline" size="sm" onClick={onCopy}>
          <Copy className="h-4 w-4" />
        </Button>
      </div>
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
