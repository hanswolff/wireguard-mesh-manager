'use client';

import { Loader2, AlertCircle, Inbox, Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { isUnauthorizedError } from '@/lib/error-handler';

interface LoadingStateProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingState({
  message = 'Loading...',
  size = 'md',
  className,
}: LoadingStateProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center space-y-2',
        className
      )}
    >
      <Loader2
        className={cn('animate-spin text-muted-foreground', sizeClasses[size])}
      />
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  action,
  icon = <Inbox className="h-12 w-12 text-muted-foreground" />,
  className,
}: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className={cn(
        'flex flex-col items-center justify-center space-y-4 text-center py-12',
        className
      )}
    >
      {icon}
      <div className="space-y-2">
        <h3 className="text-lg font-medium">{title}</h3>
        {description && (
          <p className="text-sm text-muted-foreground max-w-sm">
            {description}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  description?: string;
  error?: string | Error | unknown;
  action?: React.ReactNode;
  className?: string;
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'An error occurred while processing your request.',
  error,
  action,
  className,
}: ErrorStateProps) {
  const errorMessage = error instanceof Error ? error.message : String(error || '');

  // Check if this is an unauthorized error
  const isUnauthorized = isUnauthorizedError(error);

  // Set different UI for unauthorized errors
  const displayTitle = isUnauthorized ? 'Master Password Required' : title;
  const displayDescription = isUnauthorized
    ? 'Master password is required to access this feature. Please unlock the application first.'
    : description;
  const displayIcon = isUnauthorized ? (
    <Lock className="h-12 w-12 text-primary" />
  ) : (
    <AlertCircle className="h-12 w-12 text-destructive" />
  );
  const textClass = isUnauthorized ? 'text-foreground' : 'text-destructive';

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center space-y-4 text-center py-12',
        className
      )}
    >
      {displayIcon}
      <div className="space-y-2 max-w-md">
        <h3 className={`text-lg font-medium ${textClass}`}>{displayTitle}</h3>
        <p className="text-sm text-muted-foreground">{displayDescription}</p>
        {errorMessage && (
          <details className="text-left">
            <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
              View error details
            </summary>
            <pre className="mt-2 p-2 text-xs bg-muted rounded overflow-auto">
              {errorMessage}
            </pre>
          </details>
        )}
      </div>
      {action}
    </div>
  );
}

// Global state wrapper that can be used throughout the app
interface GlobalStateWrapperProps {
  loading?: boolean;
  error?: string | Error | null;
  empty?: boolean;
  children: React.ReactNode;
  loadingMessage?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  errorAction?: React.ReactNode;
  className?: string;
}

export function GlobalStateWrapper({
  loading = false,
  error = null,
  empty = false,
  children,
  loadingMessage,
  emptyTitle = 'No data available',
  emptyDescription = 'There are no items to display at this time.',
  emptyAction,
  errorAction,
  className,
}: GlobalStateWrapperProps) {
  if (loading) {
    return <LoadingState message={loadingMessage} className={className} />;
  }

  if (error) {
    return (
      <ErrorState error={error} action={errorAction} className={className} />
    );
  }

  if (empty) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
        className={className}
      />
    );
  }

  return <>{children}</>;
}
