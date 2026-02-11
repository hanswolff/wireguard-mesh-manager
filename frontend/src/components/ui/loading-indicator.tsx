import { cn } from '@/lib/utils';

interface LoadingIndicatorProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'h-3 w-3 border-2',
  md: 'h-4 w-4 border-b-2',
  lg: 'h-6 w-6 border-b-2',
};

export function LoadingIndicator({
  size = 'md',
  className,
}: LoadingIndicatorProps) {
  return (
    <div
      className={cn('animate-spin rounded-full border-current', sizeClasses[size], className)}
    />
  );
}
