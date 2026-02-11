import * as React from 'react';
import { Button, buttonVariants } from '@/components/ui/button';
import { LoadingIndicator } from '@/components/ui/loading-indicator';
import { cva, type VariantProps } from 'class-variance-authority';

interface LoadingButtonProps extends React.ComponentProps<'button'>,
  VariantProps<typeof buttonVariants> {
  loading?: boolean;
  loadingText?: string;
}

export function LoadingButton({
  loading = false,
  loadingText,
  children,
  disabled,
  className,
  variant = 'default',
  size = 'default',
  ...props
}: LoadingButtonProps) {
  const isDisabled = disabled || loading;

  const content = loading ? (
    <>
      <LoadingIndicator size="sm" className="mr-2" />
      {loadingText || 'Loading...'}
    </>
  ) : (
    children
  );

  return (
    <Button
      disabled={isDisabled}
      className={className}
      variant={variant}
      size={size}
      {...props}
    >
      {content}
    </Button>
  );
}
