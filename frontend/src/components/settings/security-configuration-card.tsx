'use client';

import { useState } from 'react';
import { apiClient, OperationalSettingsResponse } from '@/lib/api-client';
import { formatBytes } from '@/lib/settings-utils';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { LoadingButton } from '@/components/ui/loading-button';
import { Shield, ShieldCheck, Save } from 'lucide-react';
import { EditableList } from '@/components/ui/editable-list';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { SettingsCardHeader } from '@/components/settings/settings-card-header';
import { SettingsMetricTile } from '@/components/settings/settings-metric-tile';

interface SecurityConfigurationCardProps {
  settings: OperationalSettingsResponse;
  onSave?: () => void;
}

export function SecurityConfigurationCard({
  settings: initialSettings,
  onSave,
}: SecurityConfigurationCardProps) {
  const [settings, setSettings] = useState<OperationalSettingsResponse>(initialSettings);
  const [trustedProxies, setTrustedProxies] = useState<string[]>(
    initialSettings.trusted_proxies ? initialSettings.trusted_proxies.split(',').map(p => p.trim()) : []
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setFieldErrors({});

    try {
      // Build update payload with only changed values
      const updatePayload: any = {};

      if (settings.max_request_size !== initialSettings.max_request_size) {
        updatePayload.max_request_size = settings.max_request_size;
      }
      if (settings.request_timeout !== initialSettings.request_timeout) {
        updatePayload.request_timeout = settings.request_timeout;
      }
      if (settings.max_json_depth !== initialSettings.max_json_depth) {
        updatePayload.max_json_depth = settings.max_json_depth;
      }
      if (settings.max_string_length !== initialSettings.max_string_length) {
        updatePayload.max_string_length = settings.max_string_length;
      }
      if (settings.max_items_per_array !== initialSettings.max_items_per_array) {
        updatePayload.max_items_per_array = settings.max_items_per_array;
      }
      if (settings.rate_limit_api_key_window !== initialSettings.rate_limit_api_key_window) {
        updatePayload.rate_limit_api_key_window = settings.rate_limit_api_key_window;
      }
      if (settings.rate_limit_api_key_max_requests !== initialSettings.rate_limit_api_key_max_requests) {
        updatePayload.rate_limit_api_key_max_requests = settings.rate_limit_api_key_max_requests;
      }
      if (settings.rate_limit_ip_window !== initialSettings.rate_limit_ip_window) {
        updatePayload.rate_limit_ip_window = settings.rate_limit_ip_window;
      }
      if (settings.rate_limit_ip_max_requests !== initialSettings.rate_limit_ip_max_requests) {
        updatePayload.rate_limit_ip_max_requests = settings.rate_limit_ip_max_requests;
      }

      const newTrustedProxies = trustedProxies.join(', ');
      if (newTrustedProxies !== initialSettings.trusted_proxies) {
        updatePayload.trusted_proxies = newTrustedProxies;
      }

      if (Object.keys(updatePayload).length === 0) {
        setError('No changes to save');
        setIsSaving(false);
        return;
      }

      const updated = await apiClient.updateOperationalSettings(updatePayload);
      setSettings(updated);
      setFieldErrors({});
      setError(null);
      onSave?.();
    } catch (err: any) {
      if (err.fieldErrors) {
        setFieldErrors(err.fieldErrors);
      }
      setError(err.message || 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const validateNumberField = (field: string, value: number, min: number, max: number) => {
    if (value < min || value > max) {
      return `Value must be between ${min} and ${max}`;
    }
    return null;
  };

  return (
    <Card>
      <SettingsCardHeader
        icon={Shield}
        title="Security Configuration"
        description="Operational security settings and request hardening parameters"
        action={
          <LoadingButton
            onClick={handleSave}
            loading={isSaving}
            loadingText="Saving..."
          >
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </LoadingButton>
        }
      />
      <CardContent className="space-y-6">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div>
          <h4 className="text-sm font-medium mb-3">Request Hardening</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="maxRequestSize">Max Request Size (bytes)</Label>
              <Input
                id="maxRequestSize"
                type="number"
                value={settings.max_request_size}
                onChange={(e) => setSettings({
                  ...settings,
                  max_request_size: parseInt(e.target.value) || 0
                })}
                min={1024}
                max={104857600}
                disabled={isSaving}
              />
              {fieldErrors.max_request_size && (
                <p className="text-sm text-destructive">{fieldErrors.max_request_size}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Current: {formatBytes(settings.max_request_size)} (1KB - 100MB)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="requestTimeout">Request Timeout (seconds)</Label>
              <Input
                id="requestTimeout"
                type="number"
                value={settings.request_timeout}
                onChange={(e) => setSettings({
                  ...settings,
                  request_timeout: parseInt(e.target.value) || 0
                })}
                min={1}
                max={300}
                disabled={isSaving}
              />
              {fieldErrors.request_timeout && (
                <p className="text-sm text-destructive">{fieldErrors.request_timeout}</p>
              )}
              <p className="text-xs text-muted-foreground">
                1s - 300s (5 minutes)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxJsonDepth">Max JSON Depth</Label>
              <Input
                id="maxJsonDepth"
                type="number"
                value={settings.max_json_depth}
                onChange={(e) => setSettings({
                  ...settings,
                  max_json_depth: parseInt(e.target.value) || 0
                })}
                min={1}
                max={100}
                disabled={isSaving}
              />
              {fieldErrors.max_json_depth && (
                <p className="text-sm text-destructive">{fieldErrors.max_json_depth}</p>
              )}
              <p className="text-xs text-muted-foreground">
                1 - 100
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxStringLength">Max String Length</Label>
              <Input
                id="maxStringLength"
                type="number"
                value={settings.max_string_length}
                onChange={(e) => setSettings({
                  ...settings,
                  max_string_length: parseInt(e.target.value) || 0
                })}
                min={100}
                max={1000000}
                disabled={isSaving}
              />
              {fieldErrors.max_string_length && (
                <p className="text-sm text-destructive">{fieldErrors.max_string_length}</p>
              )}
              <p className="text-xs text-muted-foreground">
                100 - 1,000,000
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxItemsPerArray">Max Array Items</Label>
              <Input
                id="maxItemsPerArray"
                type="number"
                value={settings.max_items_per_array}
                onChange={(e) => setSettings({
                  ...settings,
                  max_items_per_array: parseInt(e.target.value) || 0
                })}
                min={1}
                max={100000}
                disabled={isSaving}
              />
              {fieldErrors.max_items_per_array && (
                <p className="text-sm text-destructive">{fieldErrors.max_items_per_array}</p>
              )}
              <p className="text-xs text-muted-foreground">
                1 - 100,000
              </p>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium mb-3">Rate Limiting</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="apiKeyWindow">API Key Window (seconds)</Label>
              <Input
                id="apiKeyWindow"
                type="number"
                value={settings.rate_limit_api_key_window}
                onChange={(e) => setSettings({
                  ...settings,
                  rate_limit_api_key_window: parseInt(e.target.value) || 0
                })}
                min={1}
                max={86400}
                disabled={isSaving}
              />
              {fieldErrors.rate_limit_api_key_window && (
                <p className="text-sm text-destructive">{fieldErrors.rate_limit_api_key_window}</p>
              )}
              <p className="text-xs text-muted-foreground">
                1s - 86400s (24 hours)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="apiKeyMaxRequests">API Key Max Requests</Label>
              <Input
                id="apiKeyMaxRequests"
                type="number"
                value={settings.rate_limit_api_key_max_requests}
                onChange={(e) => setSettings({
                  ...settings,
                  rate_limit_api_key_max_requests: parseInt(e.target.value) || 0
                })}
                min={1}
                max={1000000}
                disabled={isSaving}
              />
              {fieldErrors.rate_limit_api_key_max_requests && (
                <p className="text-sm text-destructive">{fieldErrors.rate_limit_api_key_max_requests}</p>
              )}
              <p className="text-xs text-muted-foreground">
                1 - 1,000,000
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="ipWindow">IP Window (seconds)</Label>
              <Input
                id="ipWindow"
                type="number"
                value={settings.rate_limit_ip_window}
                onChange={(e) => setSettings({
                  ...settings,
                  rate_limit_ip_window: parseInt(e.target.value) || 0
                })}
                min={1}
                max={86400}
                disabled={isSaving}
              />
              {fieldErrors.rate_limit_ip_window && (
                <p className="text-sm text-destructive">{fieldErrors.rate_limit_ip_window}</p>
              )}
              <p className="text-xs text-muted-foreground">
                1s - 86400s (24 hours)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="ipMaxRequests">IP Max Requests</Label>
              <Input
                id="ipMaxRequests"
                type="number"
                value={settings.rate_limit_ip_max_requests}
                onChange={(e) => setSettings({
                  ...settings,
                  rate_limit_ip_max_requests: parseInt(e.target.value) || 0
                })}
                min={1}
                max={1000000}
                disabled={isSaving}
              />
              {fieldErrors.rate_limit_ip_max_requests && (
                <p className="text-sm text-destructive">{fieldErrors.rate_limit_ip_max_requests}</p>
              )}
              <p className="text-xs text-muted-foreground">
                1 - 1,000,000
              </p>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium mb-3">
            Trusted Proxy Configuration
          </h4>
          <EditableList
            items={trustedProxies}
            onChange={setTrustedProxies}
            placeholder="127.0.0.1"
            label="Trusted Proxies"
            description={
              <>
                Configure trusted proxy IPs/CIDRs for X-Forwarded-For header handling.
                Examples: 127.0.0.1, ::1, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
              </>
            }
            emptyStateTitle="No trusted proxies configured"
            emptyStateDescription="Add trusted proxy IPs or CIDR ranges to handle forwarded requests"
            Icon={ShieldCheck}
            disabled={isSaving}
          />
          {fieldErrors.trusted_proxies && (
            <p className="text-sm text-destructive mt-2">{fieldErrors.trusted_proxies}</p>
          )}
        </div>

        <div>
          <h4 className="text-sm font-medium mb-3">Security Headers</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SettingsMetricTile label="Content-Type Options">
              <div className="font-mono text-sm">nosniff</div>
            </SettingsMetricTile>
            <SettingsMetricTile label="Frame Options">
              <div className="font-mono text-sm">DENY</div>
            </SettingsMetricTile>
            <SettingsMetricTile label="XSS Protection">
              <div className="font-mono text-sm">1; mode=block</div>
            </SettingsMetricTile>
            <SettingsMetricTile label="Referrer Policy">
              <div className="font-mono text-sm">strict-origin-when-cross-origin</div>
            </SettingsMetricTile>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Security headers are configured at the server level and cannot be modified through this interface.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
