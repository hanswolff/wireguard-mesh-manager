'use client';

import { OperationalSettings } from '@/lib/operational-settings';
import { Card, CardContent } from '@/components/ui/card';
import { Database } from 'lucide-react';
import { SettingsCardHeader } from '@/components/settings/settings-card-header';
import { SettingsMetricTile } from '@/components/settings/settings-metric-tile';

interface AuditConfigurationCardProps {
  settings: OperationalSettings;
}

export function AuditConfigurationCard({
  settings,
}: AuditConfigurationCardProps) {
  return (
    <Card>
      <SettingsCardHeader
        icon={Database}
        title="Audit & Logging Configuration"
        description="Audit logging retention and export settings"
      />
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SettingsMetricTile label="Audit Retention Period">
            <div className="text-lg font-semibold">
              {settings.auditRetentionDays} days
            </div>
          </SettingsMetricTile>
          <SettingsMetricTile label="Export Batch Size">
            <div className="text-lg font-semibold">
              {settings.auditExportBatchSize.toLocaleString()}
            </div>
          </SettingsMetricTile>
        </div>
      </CardContent>
    </Card>
  );
}
