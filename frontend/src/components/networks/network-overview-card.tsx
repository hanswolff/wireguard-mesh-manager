'use client';

import { WireGuardNetworkResponse } from '@/lib/api-client';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

interface NetworkOverviewCardProps {
  network: WireGuardNetworkResponse;
}

export function NetworkOverviewCard({ network }: NetworkOverviewCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Network Overview</CardTitle>
        <CardDescription>
          Summary of devices that will be included in the export
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">
              {network.device_count}
            </div>
            <p className="text-sm text-muted-foreground">Devices</p>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">
              {network.location_count}
            </div>
            <p className="text-sm text-muted-foreground">Locations</p>
          </div>
          <div className="text-center">
            <code className="text-sm bg-muted px-2 py-1 rounded">
              {network.network_cidr}
            </code>
            <p className="text-sm text-muted-foreground mt-1">Network CIDR</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
