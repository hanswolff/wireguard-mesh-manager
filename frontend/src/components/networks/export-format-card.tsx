'use client';

import { Settings, FileText, Smartphone } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { FORMAT_OPTIONS, type ExportFormat } from '@/lib/export-utils';

const ICONS = {
  wg: Settings,
  json: FileText,
  mobile: Smartphone,
} as const;

interface ExportFormatCardProps {
  value: ExportFormat;
  onValueChange: (value: ExportFormat) => void;
}

export function ExportFormatCard({
  value,
  onValueChange,
}: ExportFormatCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Configuration Format</CardTitle>
        <CardDescription>
          Choose the format for the exported device configurations
        </CardDescription>
      </CardHeader>
      <CardContent>
        <RadioGroup value={value} onValueChange={onValueChange}>
          <div className="grid gap-4">
            {FORMAT_OPTIONS.map((format) => {
              const IconComponent = ICONS[format.value];
              return (
                <div key={format.value} className="flex items-start space-x-3">
                  <RadioGroupItem
                    value={format.value}
                    id={format.value}
                    className="mt-1"
                  />
                  <div className="flex items-start space-x-3">
                    <IconComponent className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <Label
                        htmlFor={format.value}
                        className="text-sm font-medium cursor-pointer"
                      >
                        {format.title}
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        {format.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </RadioGroup>
      </CardContent>
    </Card>
  );
}
