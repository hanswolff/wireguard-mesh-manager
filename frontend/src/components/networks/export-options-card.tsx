'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { type ExportFormat } from '@/lib/export-utils';

interface ExportOptionsCardProps {
  includePresharedKeys: boolean;
  onIncludePresharedKeysChange: (value: boolean) => void;
  exportFormat: ExportFormat;
}

export function ExportOptionsCard({
  includePresharedKeys,
  onIncludePresharedKeysChange,
  exportFormat,
}: ExportOptionsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Export Options</CardTitle>
        <CardDescription>
          Configure additional settings for the export
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="include-preshared-keys"
            checked={includePresharedKeys}
            onCheckedChange={(checked) =>
              onIncludePresharedKeysChange(checked as boolean)
            }
          />
          <div className="grid gap-1.5 leading-none">
            <Label
              htmlFor="include-preshared-keys"
              className="text-sm font-normal"
            >
              Include Preshared Keys
            </Label>
            <p className="text-xs text-muted-foreground">
              Include preshared keys in the configuration files (if any devices
              have them configured)
            </p>
          </div>
        </div>

        <Separator />

        <div className="text-sm text-muted-foreground">
          <strong>Export Contents:</strong>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>All device configuration files ({exportFormat} format)</li>
            <li>Network server configuration</li>
            <li>Network summary README file</li>
            <li>Error report for any failed device exports</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
