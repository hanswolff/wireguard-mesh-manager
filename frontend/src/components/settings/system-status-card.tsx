'use client';

import { HealthCheckResponse } from '@/lib/api-client';
import {
  getStatusIcon,
  getStatusBadgeVariant,
  formatUptime,
} from '@/lib/settings-utils';
import {
  Card,
  CardContent,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, AlertCircle, Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { SettingsCardHeader } from '@/components/settings/settings-card-header';
import { SettingsMetricTile } from '@/components/settings/settings-metric-tile';

interface SystemStatusCardProps {
  healthData: HealthCheckResponse | null;
  loading?: boolean;
}

function StatusIcon({ icon }: { icon: LucideIcon }) {
  const Icon = icon;
  return <Icon className="h-4 w-4" />;
}

export function SystemStatusCard({ healthData, loading }: SystemStatusCardProps) {
  return (
    <Card>
      <SettingsCardHeader
        icon={Activity}
        title="System Status"
        description="Current health and operational status of WireGuard Mesh Manager"
      />
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            <span>Loading health status...</span>
          </div>
        ) : healthData ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <SettingsMetricTile label="Overall Status" layout="inline">
              <Badge
                variant={getStatusBadgeVariant(healthData.status)}
                className="flex items-center gap-1"
              >
                <StatusIcon icon={getStatusIcon(healthData.status)} />
                {healthData.status}
              </Badge>
            </SettingsMetricTile>
            <SettingsMetricTile label="Database" layout="inline">
              <Badge
                variant={getStatusBadgeVariant(healthData.database_status)}
                className="flex items-center gap-1"
              >
                <StatusIcon icon={getStatusIcon(healthData.database_status)} />
                {healthData.database_status}
              </Badge>
            </SettingsMetricTile>
            <SettingsMetricTile label="Version" layout="inline">
              <span className="text-sm font-mono">{healthData.version}</span>
            </SettingsMetricTile>
            <SettingsMetricTile label="Uptime" layout="inline">
              <span className="text-sm font-mono">
                {formatUptime(healthData.uptime_seconds)}
              </span>
            </SettingsMetricTile>
          </div>
        ) : (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <AlertCircle className="h-5 w-5 mr-2" />
            <span>Unable to load health status</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
