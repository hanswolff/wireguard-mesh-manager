import { Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { formatTimeRemaining } from '@/lib/utils/time-formatters';

interface TimerBadgeProps {
  expiresAt: string;
}

export function TimerBadge({ expiresAt }: TimerBadgeProps) {
  return (
    <Badge
      variant="outline"
      className="ml-2 h-5 text-[10px] px-1 border-success-border bg-success-surface dark:text-white dark:border-success-foreground"
    >
      <Clock className="h-3 w-3 mr-1" />
      {formatTimeRemaining(expiresAt)}
    </Badge>
  );
}
