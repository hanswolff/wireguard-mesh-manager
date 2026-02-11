import { useState } from 'react';
import { Key, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { type DeviceResponse } from '@/lib/api-client';
import { useCopyToClipboard } from './use-copy-to-clipboard';

interface ApiManagementTabProps {
  device: DeviceResponse;
  onRegenerateApiKey: () => Promise<void>;
  isRegeneratingKey: boolean;
  newApiKey: string;
  showNewApiKey: boolean;
  onApiKeyGenerated: (apiKey: string) => void;
}

export function ApiManagementTab({
  device,
  onRegenerateApiKey,
  isRegeneratingKey,
  newApiKey,
  showNewApiKey,
  onApiKeyGenerated,
}: ApiManagementTabProps) {
  const { copyToClipboard, isCopied } = useCopyToClipboard();

  return (
    <Card>
      <CardHeader>
        <CardTitle>API Key Management</CardTitle>
        <CardDescription>
          Manage the device&apos;s API key for configuration retrieval
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <FieldLabel>API Key Status</FieldLabel>
            <Badge variant={device.api_key ? 'default' : 'secondary'}>
              {device.api_key ? 'Generated' : 'Not Generated'}
            </Badge>
          </div>
          <div>
            <FieldLabel>Last Used</FieldLabel>
            <p className="text-sm">
              {device.api_key_last_used
                ? new Date(device.api_key_last_used).toLocaleString()
                : 'Never used'}
            </p>
          </div>
        </div>

        <Separator />

        <div className="flex items-center space-x-2">
          <ApiKeyRegenerateDialog
            onRegenerate={onRegenerateApiKey}
            isRegenerating={isRegeneratingKey}
            onApiKeyGenerated={onApiKeyGenerated}
          />
        </div>

        {newApiKey && showNewApiKey && (
          <ApiKeyDisplay
            apiKey={newApiKey}
            isCopied={isCopied}
            onCopy={copyToClipboard}
          />
        )}

        {device.endpoint_allowlist && device.endpoint_allowlist.length > 0 && (
          <>
            <Separator />
            <EndpointAllowlist endpoints={device.endpoint_allowlist} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ApiKeyRegenerateDialog({
  onRegenerate,
  isRegenerating,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onApiKeyGenerated,
}: {
  onRegenerate: () => Promise<void>;
  isRegenerating: boolean;
  onApiKeyGenerated: (apiKey: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);

  const handleRegenerate = async () => {
    await onRegenerate();
    setIsOpen(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" disabled={isRegenerating}>
          <RefreshCw
            className={`h-4 w-4 mr-2 ${isRegenerating ? 'animate-spin' : ''}`}
          />
          Regenerate API Key
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Regenerate API Key</DialogTitle>
          <DialogDescription>
            This will generate a new API key for the device. The old key will
            become invalid. The new key will only be shown once, so please save
            it securely.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <LoadingButton
            onClick={handleRegenerate}
            loading={isRegenerating}
            loadingText="Generating..."
          >
            Generate New Key
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ApiKeyDisplay({
  apiKey,
  isCopied,
  onCopy,
}: {
  apiKey: string;
  isCopied: boolean;
  onCopy: (text: string, type: string) => void;
}) {
  return (
    <Alert>
      <Key className="h-4 w-4" />
      <AlertDescription>
        <div className="space-y-2">
          <p className="font-medium">New API Key (save this securely):</p>
          <div className="flex items-center space-x-2">
            <code className="text-sm bg-muted px-2 py-1 rounded flex-1 break-all">
              {apiKey}
            </code>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onCopy(apiKey, 'API Key')}
            >
              {isCopied ? '✓' : <Key className="h-4 w-4" />}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            This key will not be shown again. Make sure to save it in a secure
            location.
          </p>
        </div>
      </AlertDescription>
    </Alert>
  );
}

function EndpointAllowlist({ endpoints }: { endpoints: string[] }) {
  return (
    <div>
      <FieldLabel>Endpoint Allowlist</FieldLabel>
      <div className="space-y-1">
        {endpoints.map((endpoint, index) => (
          <code
            key={index}
            className="text-sm bg-muted px-2 py-1 rounded block"
          >
            {endpoint}
          </code>
        ))}
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
