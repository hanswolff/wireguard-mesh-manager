'use client';

import { OperationalSettings } from '@/lib/operational-settings';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Key } from 'lucide-react';
import { SettingsCardHeader } from '@/components/settings/settings-card-header';
import { SettingsMetricTile } from '@/components/settings/settings-metric-tile';

interface MasterPasswordCacheCardProps {
  settings: OperationalSettings;
}

export function MasterPasswordCacheCard({
  settings,
}: MasterPasswordCacheCardProps) {
  return (
    <Card>
      <SettingsCardHeader
        icon={Key}
        title="Master Password Cache Configuration"
        description="In-memory caching settings for master password unlock state"
      />
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SettingsMetricTile label="Cache TTL">
            <div className="text-lg font-semibold">
              {settings.masterPasswordTtlHours}h
            </div>
          </SettingsMetricTile>
          <SettingsMetricTile label="Idle Timeout">
            <div className="text-lg font-semibold">
              {settings.masterPasswordIdleTimeoutMinutes}m
            </div>
          </SettingsMetricTile>
          <SettingsMetricTile label="Per-User Session">
            <Badge
              variant={
                settings.masterPasswordPerUserSession ? 'default' : 'secondary'
              }
            >
              {settings.masterPasswordPerUserSession ? 'Enabled' : 'Disabled'}
            </Badge>
          </SettingsMetricTile>
        </div>
      </CardContent>
    </Card>
  );
}
