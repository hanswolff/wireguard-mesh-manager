import {
  Shield,
  CheckCircle,
  XCircle,
  AlertCircle,
  Info,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { type ConfigLintResponse, type LintIssue } from '@/lib/api-client';

interface ConfigLintStatusProps {
  lintResults: ConfigLintResponse | null;
  lintLoading: boolean;
  onRefresh: () => void;
}

const severityConfig = {
  error: {
    surface: 'bg-destructive-surface border-destructive-border',
    icon: XCircle,
    badgeVariant: 'destructive' as const,
    badgeClass:
      'bg-destructive-surface text-destructive-foreground border-destructive-border',
    iconColor: 'text-destructive',
  },
  warning: {
    surface: 'bg-warning-surface border-warning-border',
    icon: AlertCircle,
    badgeVariant: 'outline' as const,
    badgeClass:
      'bg-warning-surface text-warning-foreground border-warning-border',
    iconColor: 'text-warning',
  },
  info: {
    surface: 'bg-info-surface border-info-border',
    icon: Info,
    badgeVariant: 'outline' as const,
    badgeClass: 'bg-info-surface text-info-foreground border-info-border',
    iconColor: 'text-info',
  },
} as const;

export function ConfigLintStatus({
  lintResults,
  lintLoading,
  onRefresh,
}: ConfigLintStatusProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <span>Configuration Validation</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={lintLoading}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${lintLoading ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
        </CardTitle>
        <CardDescription>
          Automated validation of network configuration for common issues
        </CardDescription>
      </CardHeader>
      <CardContent>
        {lintLoading ? (
          <LoadingState />
        ) : lintResults ? (
          <ConfigLintResults results={lintResults} />
        ) : (
          <EmptyState />
        )}
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center space-x-2">
      <RefreshCw className="h-4 w-4 animate-spin" />
      <span>Validating configuration...</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-4">
      <Shield className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
      <p className="text-muted-foreground">
        Configuration validation not yet performed
      </p>
    </div>
  );
}

function ConfigLintResults({ results }: { results: ConfigLintResponse }) {
  return (
    <div className="space-y-4">
      <OverallStatus
        valid={results.valid}
        summary={results.summary}
        issues={results.issues}
      />
      <IssueCounts issueCount={results.issue_count} />
      {results.issues.length > 0 && <IssuesList issues={results.issues} />}
    </div>
  );
}

function OverallStatus({
  valid,
  summary,
  issues,
}: {
  valid: boolean;
  summary: string;
  issues: LintIssue[];
}) {
  const statusText = valid
    ? 'Configuration is valid'
    : 'Configuration has issues';
  const statusColor = valid
    ? 'text-success'
    : issues.some((issue) => issue.severity === 'error')
      ? 'text-destructive'
      : 'text-warning-foreground';

  return (
    <div className="flex items-center space-x-3">
      {valid ? (
        <CheckCircle className={`h-6 w-5 ${statusColor}`} />
      ) : (
        <DynamicIcon
          icon={getStatusIcon(issues)}
          className={`h-6 w-5 ${statusColor}`}
        />
      )}
      <div>
        <p className="font-medium">{statusText}</p>
        <p className="text-sm text-muted-foreground">{summary}</p>
      </div>
    </div>
  );
}

function DynamicIcon({
  icon: Icon,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>;
  className?: string;
}) {
  return <Icon className={className} />;
}

function IssueCounts({ issueCount }: { issueCount: Record<string, number> }) {
  if (Object.keys(issueCount).length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {issueCount.error > 0 && (
        <Badge
          variant={severityConfig.error.badgeVariant}
          className={`bg-destructive-surface text-destructive-foreground border border-destructive-border`}
        >
          {issueCount.error} Error{issueCount.error > 1 ? 's' : ''}
        </Badge>
      )}
      {issueCount.warning > 0 && (
        <Badge
          variant={severityConfig.warning.badgeVariant}
          className={`border ${severityConfig.warning.badgeClass}`}
        >
          {issueCount.warning} Warning{issueCount.warning > 1 ? 's' : ''}
        </Badge>
      )}
      {issueCount.info > 0 && (
        <Badge
          variant={severityConfig.info.badgeVariant}
          className={`border ${severityConfig.info.badgeClass}`}
        >
          {issueCount.info} Info{issueCount.info > 1 ? 's' : ''}
        </Badge>
      )}
    </div>
  );
}

function IssuesList({ issues }: { issues: LintIssue[] }) {
  return (
    <div className="space-y-2">
      <h4 className="font-medium">Issues Found:</h4>
      <div className="space-y-2">
        {issues.map((issue, index) => (
          <IssueItem key={index} issue={issue} />
        ))}
      </div>
    </div>
  );
}

function IssueItem({ issue }: { issue: LintIssue }) {
  const SeverityIcon =
    severityConfig[issue.severity]?.icon || severityConfig.info.icon;
  const severity = severityConfig[issue.severity] || severityConfig.info;
  const surfaceClass = severity.surface;

  return (
    <div
      className={`flex items-start space-x-3 p-3 rounded-lg border ${surfaceClass}`}
    >
      <div className="flex-shrink-0 mt-0.5">
        <SeverityIcon
          className={`h-4 w-4 ${severity.iconColor ?? 'text-info'}`}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2 mb-1">
          <span className="font-medium capitalize">{issue.category}</span>
          <span className="text-sm text-muted-foreground">•</span>
          <span className="text-sm font-mono bg-muted px-1 rounded">
            {issue.field}
          </span>
        </div>
        <p className="text-sm">{issue.message}</p>
        {issue.suggestion && (
          <p className="text-sm text-muted-foreground mt-1">
            <em>Suggestion: {issue.suggestion}</em>
          </p>
        )}
      </div>
    </div>
  );
}

function getStatusIcon(issues: LintIssue[]) {
  return issues.some((i) => i.severity === 'error') ? XCircle : AlertCircle;
}
