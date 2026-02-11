'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  apiClient,
  AuditEventList,
  AuditEventParams,
  AuditExportParams,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { GlobalStateWrapper, EmptyState } from '@/components/global-states';
import { AuditFilters } from '@/components/audit-filters';
import { Download, Filter, RefreshCw, Inbox, Lock } from 'lucide-react';
import { format as formatDate } from 'date-fns';
import { getActionColor } from '@/constants/audit';
import {
  ApiError,
  getErrorMessage,
  isUnauthorizedError,
} from '@/lib/error-handler';
import { useUnlock } from '@/contexts/unlock-context';
import { MasterPasswordUnlockModal } from '@/components/ui/master-password-unlock-modal';

export default function AuditPage() {
  const [auditData, setAuditData] = useState<AuditEventList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const { isUnlocked } = useUnlock();

  const [filters, setFilters] = useState<AuditEventParams>({
    page: 1,
    page_size: 50,
    include_details: false,
  });

  const normalizeError = (err: unknown, context: string): ApiError => {
    const errorMessage = getErrorMessage(err, context);
    const normalizedError: ApiError =
      err instanceof Error
        ? (err as ApiError)
        : (new Error(errorMessage) as ApiError);

    if (err && typeof err === 'object' && 'status' in err) {
      normalizedError.status = (err as ApiError).status;
    }

    normalizedError.message = errorMessage;
    return normalizedError;
  };

  const refreshAuditEvents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAuditEvents(filters);
      setAuditData(data);
    } catch (err) {
      const normalizedError = normalizeError(err, 'audit events');
      setError(normalizedError);

      // If it's an unauthorized error, show the unlock modal
      if (isUnauthorizedError(normalizedError) && !isUnlocked) {
        setShowUnlockModal(true);
      }
    } finally {
      setLoading(false);
    }
  }, [filters, isUnlocked]);

  useEffect(() => {
    refreshAuditEvents();
  }, [refreshAuditEvents]);

  const handleFilterChange = (
    key: keyof AuditEventParams,
    value: string | number | boolean | undefined
  ) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      page: key !== 'page' ? 1 : typeof value === 'number' ? value : prev.page, // Reset to page 1 when changing filters (except when changing page)
    }));
  };

  const clearFilters = useCallback(() => {
    setFilters({
      page: 1,
      page_size: 50,
      include_details: false,
    });
  }, []);

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      setExporting(true);
      const exportParams: AuditExportParams = {
        network_id: filters.network_id,
        start_date: filters.start_date,
        end_date: filters.end_date,
        actor: filters.actor,
        action: filters.action,
        resource_type: filters.resource_type,
        format,
        include_details: true,
      };

      const downloadUrl = await apiClient.exportAuditEvents(exportParams);

      // Create download link
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `audit_events_${format}_${formatDate(new Date(), 'yyyyMMdd_HHmmss')}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up blob URL
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 100);
    } catch (err) {
      setError(normalizeError(err, 'audit export'));
    } finally {
      setExporting(false);
    }
  };

  const hasActiveFilters = Object.entries(filters).some(
    ([key, value]) =>
      !['page', 'page_size', 'include_details'].includes(key) &&
      value !== undefined &&
      value !== ''
  );

  const content = (
    <div className="space-y-6">
      {error && (
        <Alert
          variant={isUnauthorizedError(error) ? 'default' : 'destructive'}
          className={isUnauthorizedError(error) ? 'border-primary' : ''}
        >
          {isUnauthorizedError(error) && <Lock className="h-4 w-4" />}
          <AlertDescription className="ml-2">
            {getErrorMessage(error, 'audit events')}
            {isUnauthorizedError(error) && !isUnlocked && (
              <Button
                variant="link"
                className="ml-2 p-0 h-auto"
                onClick={() => setShowUnlockModal(true)}
              >
                Unlock Now
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Controls Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4 items-center justify-between">
            <div className="flex gap-2 items-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
                {hasActiveFilters && (
                  <Badge variant="secondary" className="ml-2">
                    Active
                  </Badge>
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('json')}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('csv')}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
            </div>
            <div className="flex gap-2 items-center">
              <Button
                variant="outline"
                size="sm"
                onClick={refreshAuditEvents}
                disabled={loading}
                aria-label="Refresh audit events"
              >
                <RefreshCw
                  className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`}
                />
                Refresh
              </Button>
            </div>
          </div>

          {showFilters && (
            <AuditFilters
              filters={filters}
              onFilterChange={handleFilterChange}
              onClearFilters={clearFilters}
              hasActiveFilters={hasActiveFilters}
            />
          )}
        </CardContent>
      </Card>

      {/* Results Table */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Audit Events</CardTitle>
              {auditData && (
                <CardDescription>
                  Showing {auditData.events.length} of{' '}
                  {auditData.pagination.total_count} events
                </CardDescription>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {auditData && auditData.events.length > 0 ? (
            <div className="space-y-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">Timestamp</TableHead>
                      <TableHead scope="col">Actor</TableHead>
                      <TableHead scope="col">Action</TableHead>
                      <TableHead scope="col">Resource</TableHead>
                      <TableHead scope="col">Network</TableHead>
                      {filters.include_details && (
                        <TableHead scope="col">Details</TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {auditData.events.map((event) => (
                      <TableRow key={event.id}>
                        <TableCell className="font-mono text-sm">
                          {formatDate(
                            new Date(event.created_at),
                            'yyyy-MM-dd HH:mm:ss'
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {event.actor}
                        </TableCell>
                        <TableCell>
                          <Badge variant={getActionColor(event.action)}>
                            {event.action}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">
                              {event.resource_type}
                            </div>
                            {event.resource_id && (
                              <div className="text-xs text-muted-foreground font-mono">
                                {event.resource_id.slice(0, 8)}...
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            {event.network_name && (
                              <div className="font-medium">
                                {event.network_name}
                              </div>
                            )}
                            <div className="text-xs text-muted-foreground font-mono">
                              {event.network_id.slice(0, 8)}...
                            </div>
                          </div>
                        </TableCell>
                        {filters.include_details && (
                          <TableCell className="max-w-xs">
                            {event.details ? (
                              <div className="text-xs font-mono bg-muted p-2 rounded overflow-hidden">
                                <pre className="whitespace-pre-wrap break-all">
                                  {JSON.stringify(event.details, null, 2)}
                                </pre>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">
                                No details
                              </span>
                            )}
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {auditData.pagination.total_pages > 1 && (
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Page {auditData.pagination.page} of{' '}
                    {auditData.pagination.total_pages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        handleFilterChange(
                          'page',
                          auditData.pagination.page - 1
                        )
                      }
                      disabled={!auditData.pagination.has_previous}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        handleFilterChange(
                          'page',
                          auditData.pagination.page + 1
                        )
                      }
                      disabled={!auditData.pagination.has_next}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              title="No audit events found"
              description="No audit events match your current filter criteria."
              action={
                hasActiveFilters && (
                  <Button onClick={clearFilters}>Clear filters</Button>
                )
              }
              icon={<Inbox className="h-12 w-12 text-muted-foreground" />}
              data-testid="empty-state"
            />
          )}
        </CardContent>
      </Card>
    <MasterPasswordUnlockModal isOpen={showUnlockModal} onClose={() => setShowUnlockModal(false)} />

    </div>
  );

  const loadingSkeleton = (
    <div className="space-y-6">
      <div className="space-y-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    <MasterPasswordUnlockModal isOpen={showUnlockModal} onClose={() => setShowUnlockModal(false)} />

    </div>
  );

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Audit Events</h1>
        <p className="text-muted-foreground">
          View and filter system audit events for security and compliance
          monitoring.
        </p>
      </div>

      <GlobalStateWrapper
        loading={loading && !auditData}
        loadingMessage="Loading audit events..."
        error={error}
        empty={
          !!(auditData && auditData.events.length === 0 && !hasActiveFilters)
        }
        emptyTitle="No audit events"
        emptyDescription="No audit events have been recorded yet."
        errorAction={
          <Button
            onClick={() => {
              setError(null);
              refreshAuditEvents();
            }}
          >
            Try Again
          </Button>
        }
      >
        {loading && !auditData ? loadingSkeleton : content}
      </GlobalStateWrapper>
    <MasterPasswordUnlockModal isOpen={showUnlockModal} onClose={() => setShowUnlockModal(false)} />

    </div>
  );
}
