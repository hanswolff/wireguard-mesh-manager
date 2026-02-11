import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LucideIcon, TrendingUp } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: React.ReactNode;
  icon: LucideIcon;
  description?: string;
  trend?: number;
  valueAsCode?: boolean;
  valueClassName?: string;
  truncateValue?: boolean;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  valueAsCode = false,
  valueClassName,
  truncateValue = false,
}: StatCardProps) {
  const ValueComponent = valueAsCode ? 'code' : 'div';
  const resolvedValueClassName =
    valueClassName ??
    (valueAsCode ? 'text-2xl font-mono tracking-tight' : 'text-2xl font-bold');

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <ValueComponent
          className={`${resolvedValueClassName} ${truncateValue ? 'truncate' : ''}`}
        >
          {value}
        </ValueComponent>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {trend !== undefined && (
          <div className="flex items-center text-xs text-muted-foreground mt-1">
            <TrendingUp className="h-3 w-3 mr-1" />
            {trend > 0 ? '+' : ''}
            {trend}% from last period
          </div>
        )}
      </CardContent>
    </Card>
  );
}
