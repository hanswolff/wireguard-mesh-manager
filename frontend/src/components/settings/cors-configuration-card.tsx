'use client';

import { useState } from 'react';
import { OperationalSettings } from '@/lib/operational-settings';
import {
  Card,
  CardContent,
} from '@/components/ui/card';
import { Network, Globe } from 'lucide-react';
import { EditableList } from '@/components/ui/editable-list';
import { SettingsCardHeader } from '@/components/settings/settings-card-header';

interface CorsConfigurationCardProps {
  settings: OperationalSettings;
}

export function CorsConfigurationCard({
  settings,
}: CorsConfigurationCardProps) {
  const [origins, setOrigins] = useState<string[]>(
    settings.corsOrigins || []
  );

  return (
    <Card>
      <SettingsCardHeader
        icon={Network}
        title="CORS Configuration"
        description="Cross-Origin Resource Sharing (CORS) settings for API access"
      />
      <CardContent>
        <EditableList
          items={origins}
          onChange={setOrigins}
          placeholder="https://example.com"
          label="Allowed Origins"
          description="Note: These are the allowed origins for cross-origin requests. Only origins listed here can access the API from browsers. Use full URLs with protocol (e.g., https://example.com)."
          emptyStateTitle="No CORS origins configured"
          emptyStateDescription="Add an origin to enable cross-origin requests"
          Icon={Globe}
        />
      </CardContent>
    </Card>
  );
}
