'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, AuditStatistics, HealthCheckResponse } from '@/lib/api';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GlobalStateWrapper } from '@/components/global-states';
import { StatCard } from '@/components/stat-card';
import { Activity, Shield, Server, Clock, Database, FileText, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import {
  getErrorMessage,
  isUnauthorizedError,
} from '@/lib/error-handler';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';
import { useUnlock } from '@/contexts/unlock-context';
import { SystemStatusCard } from '@/components/settings/system-status-card';

export const dynamic = 'force-dynamic';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export default function Home() {
  const [stats, setStats] = useState<AuditStatistics | null>(null);
  const [healthData, setHealthData] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [healthLoading, setHealthLoading] = useState(true);
  const [error, setError] = useState<string | Error | null>(null);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const { } = useUnlock();

  const refreshHealthStatus = useCallback(async () => {
    try {
      setHealthLoading(true);
      const data = await apiClient.getHealth();
      setHealthData(data);
    } catch (err) {
      // Don't show error for health check failure - just log it
      console.error('Failed to fetch health status:', err);
      setHealthData(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setError(null);
        const [auditStats, healthResponse] = await Promise.allSettled([
          apiClient.getAuditStatistics(),
          apiClient.getHealth(),
        ]);

        if (auditStats.status === 'fulfilled') {
          setStats(auditStats.value);
        } else {
          const errorMessage = getErrorMessage(auditStats.reason, 'audit statistics');
          if (isUnauthorizedError(auditStats.reason)) {
            setShowUnlockModal(true);
          } else {
            setError(errorMessage);
          }
        }

        if (healthResponse.status === 'fulfilled') {
          setHealthData(healthResponse.value);
        } else {
          console.error('Failed to fetch health status:', healthResponse.reason);
          setHealthData(null);
        }
      } finally {
        setLoading(false);
        setHealthLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleUnlockSuccess = () => {
    // Refresh data after successful unlock
    const fetchData = async () => {
      try {
        setError(null);
        setLoading(true);
        setHealthLoading(true);

        const [auditStats, healthResponse] = await Promise.allSettled([
          apiClient.getAuditStatistics(),
          apiClient.getHealth(),
        ]);

        if (auditStats.status === 'fulfilled') {
          setStats(auditStats.value);
        } else {
          const errorMessage = getErrorMessage(auditStats.reason, 'audit statistics');
          if (isUnauthorizedError(auditStats.reason)) {
            setShowUnlockModal(true);
          } else {
            setError(errorMessage);
          }
        }

        if (healthResponse.status === 'fulfilled') {
          setHealthData(healthResponse.value);
        } else {
          console.error('Failed to fetch health status:', healthResponse.reason);
          setHealthData(null);
        }

        setLoading(false);
        setHealthLoading(false);
      } catch (err) {
        const errorMessage = getErrorMessage(err, 'audit statistics');
        if (isUnauthorizedError(err)) {
          setShowUnlockModal(true);
        } else {
          setError(errorMessage);
        }
        setLoading(false);
        setHealthLoading(false);
      }
    };

    fetchData();
  };

  const content = (
    <div className="space-y-6">
      <SystemStatusCard healthData={healthData} loading={healthLoading} />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Events"
          value={stats?.total_events?.toLocaleString() || '0'}
          icon={Activity}
          description="All-time audit events"
        />
        <StatCard
          title="Last 24 Hours"
          value={stats?.recent_events_24h?.toLocaleString() || '0'}
          icon={Clock}
          description="Events in last 24 hours"
        />
        <StatCard
          title="Last 7 Days"
          value={stats?.recent_events_7d?.toLocaleString() || '0'}
          icon={Shield}
          description="Events in last 7 days"
        />
        <StatCard
          title="Total Storage"
          value={formatBytes(stats?.storage_stats?.total_size_bytes || 0)}
          icon={Server}
          description="Database and files"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Audit & Security
          </CardTitle>
          <CardDescription>
            Monitor system events and maintain security compliance
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Link href="/audit">
            <Button>
              <Activity className="h-4 w-4 mr-2" />
              View Audit Events
            </Button>
          </Link>

          {/* Last 24 Hours and Last 7 Days - Side by Side */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Last 24 Hours Events Summary */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <h2 className="font-semibold">Last 24 Hours</h2>
                <Badge variant="secondary">
                  {stats?.recent_events_24h?.toLocaleString() || '0'}
                </Badge>
              </div>
              {stats?.recent_actions_breakdown_24h &&
                stats.recent_actions_breakdown_24h.length > 0 ? (
                <div className="space-y-2">
                  {stats.recent_actions_breakdown_24h.slice(0, 5).map((item) => (
                    <div
                      key={item.action}
                      className="flex items-center justify-between text-sm p-2 rounded bg-muted/50"
                    >
                      <Badge variant={item.action.includes('DELETE') || item.action.includes('FAILED') ? 'destructive' : 'secondary'}>
                        {item.action}
                      </Badge>
                      <span className="font-medium">{item.count}</span>
                    </div>
                  ))}
                  {stats.recent_actions_breakdown_24h.length > 5 && (
                    <p className="text-xs text-muted-foreground text-center">
                      + {stats.recent_actions_breakdown_24h.length - 5} more
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No events</p>
              )}
            </div>

            {/* Last 7 Days Events Summary */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-muted-foreground" />
                <h2 className="font-semibold">Last 7 Days</h2>
                <Badge variant="secondary">
                  {stats?.recent_events_7d?.toLocaleString() || '0'}
                </Badge>
              </div>
              {stats?.recent_actions_breakdown_7d &&
                stats.recent_actions_breakdown_7d.length > 0 ? (
                <div className="space-y-2">
                  {stats.recent_actions_breakdown_7d.slice(0, 5).map((item) => (
                    <div
                      key={item.action}
                      className="flex items-center justify-between text-sm p-2 rounded bg-muted/50"
                    >
                      <Badge variant={item.action.includes('DELETE') || item.action.includes('FAILED') ? 'destructive' : 'secondary'}>
                        {item.action}
                      </Badge>
                      <span className="font-medium">{item.count}</span>
                    </div>
                  ))}
                  {stats.recent_actions_breakdown_7d.length > 5 && (
                    <p className="text-xs text-muted-foreground text-center">
                      + {stats.recent_actions_breakdown_7d.length - 5} more
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No events</p>
              )}
            </div>
          </div>

          {/* Security Highlights */}
          {stats?.recent_actions_breakdown_7d &&
            stats.recent_actions_breakdown_7d.some(
              (item) => item.action.includes('DELETE') || item.action.includes('FAILED') || item.action.includes('UNAUTHORIZED')
            ) && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-destructive" />
                <h2 className="font-semibold text-destructive">Security Alerts</h2>
              </div>
              <ul className="space-y-1 text-sm">
                {stats.recent_actions_breakdown_7d
                  .filter((item) => item.action.includes('DELETE') || item.action.includes('FAILED') || item.action.includes('UNAUTHORIZED'))
                  .map((item) => (
                    <li key={item.action} className="flex justify-between">
                      <span>{item.action}</span>
                      <Badge variant="destructive" className="ml-2">{item.count}</Badge>
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {stats?.storage_stats?.breakdown && stats.storage_stats.breakdown.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Storage Breakdown
            </CardTitle>
            <CardDescription>
              Detailed view of database and related files
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {stats.storage_stats.breakdown.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate text-sm">
                        {item.file}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {item.type}
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    <div className="font-semibold text-sm">
                      {formatBytes(item.size_bytes)}
                    </div>
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border-t">
                <div className="font-medium">
                  Total Storage
                </div>
                <div className="font-bold">
                  {formatBytes(stats.storage_stats.total_size_bytes)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor your WireGuard cluster security and activity at a glance.
        </p>
      </div>

      <GlobalStateWrapper
        loading={loading}
        loadingMessage="Loading dashboard statistics..."
        error={error}
        empty={false}
        errorAction={<Button onClick={() => window.location.reload()}>Try Again</Button>}
      >
        {content}
      </GlobalStateWrapper>

      <div suppressHydrationWarning>
        <MasterPasswordUnlockModal
          isOpen={showUnlockModal}
          onClose={() => setShowUnlockModal(false)}
          onSuccess={handleUnlockSuccess}
        />
      </div>
    </div>
  );
}
