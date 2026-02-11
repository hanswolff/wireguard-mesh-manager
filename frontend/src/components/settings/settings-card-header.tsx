import type { LucideIcon } from 'lucide-react';
import {
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

interface SettingsCardHeaderProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function SettingsCardHeader({
  icon: Icon,
  title,
  description,
  action,
}: SettingsCardHeaderProps) {
  return (
    <CardHeader>
      <div className="flex items-center justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Icon className="h-5 w-5" />
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        {action}
      </div>
    </CardHeader>
  );
}
