'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Download } from 'lucide-react';
import { type ExportFormat } from '@/lib/export-utils';

interface ExportActionCardProps {
  networkName: string;
  deviceCount: number;
  exportFormat: ExportFormat;
  includePresharedKeys: boolean;
  isExporting: boolean;
  onExport: () => void;
}

export function ExportActionCard({
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  networkName,
  deviceCount,
  exportFormat,
  includePresharedKeys,
  isExporting,
  onExport,
}: ExportActionCardProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">Ready to Export</h3>
            <p className="text-sm text-muted-foreground">
              Export {deviceCount} device configurations in{' '}
              {exportFormat.toUpperCase()} format
              {includePresharedKeys && ' with preshared keys'}
            </p>
          </div>
          <Button onClick={onExport} disabled={isExporting} size="lg">
            {isExporting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Export Configs
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
