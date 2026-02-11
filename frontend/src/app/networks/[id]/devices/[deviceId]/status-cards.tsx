import { Cpu, Globe, MapPin, Key } from 'lucide-react';
import { StatCard } from '@/components/stat-card';
import { type DeviceResponse } from '@/lib/api-client';

interface StatusCardsProps {
  device: DeviceResponse;
}

export function StatusCards({ device }: StatusCardsProps) {
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Status"
        value={device.enabled ? 'Active' : 'Inactive'}
        icon={Cpu}
        description="device status"
        truncateValue={true}
      />
      <StatCard
        title="WireGuard IP"
        value={device.wireguard_ip || 'Not assigned'}
        icon={Globe}
        description="VPN IP address"
        valueAsCode={true}
      />
      <StatCard
        title="Location"
        value={device.location_name || 'Unknown'}
        icon={MapPin}
        description="network location"
        truncateValue={true}
      />
      <StatCard
        title="API Key"
        value={device.api_key ? 'Generated' : 'Not set'}
        icon={Key}
        description="authentication key"
        truncateValue={true}
      />
    </div>
  );
}
