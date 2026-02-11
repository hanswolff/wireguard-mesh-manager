import { useState, useEffect, useCallback } from 'react';
import { toast } from '@/components/ui/use-toast';
import apiClient, {
  type ConfigLintRequest,
  type ConfigLintResponse,
  type WireGuardNetworkResponse,
  type LocationResponse,
  type DeviceResponse,
} from '@/lib/api-client';

export function useConfigLint(network: WireGuardNetworkResponse | null) {
  const [lintResults, setLintResults] = useState<ConfigLintResponse | null>(
    null
  );
  const [lintLoading, setLintLoading] = useState(false);

  const buildLintRequest = useCallback(
    async (
      networkData: WireGuardNetworkResponse
    ): Promise<ConfigLintRequest> => {
      const [locations, devices] = await Promise.all([
        apiClient.listLocations({ network_id: networkData.id }),
        apiClient.listDevices({ network_id: networkData.id }),
      ]);

      return {
        network_cidr: networkData.network_cidr,
        dns_servers: networkData.dns_servers ?? undefined,
        mtu: networkData.mtu ?? undefined,
        persistent_keepalive: networkData.persistent_keepalive ?? undefined,
        locations: locations.map(locationToLint),
        devices: devices.map(deviceToLint),
      };
    },
    []
  );

  const performConfigLint = useCallback(async () => {
    if (!network) return;

    try {
      setLintLoading(true);
      const lintRequest = await buildLintRequest(network);
      const results = await apiClient.lintNetworkConfig(lintRequest);
      setLintResults(results);
    } catch (error) {
      toast({
        title: 'Config Lint Failed',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to validate network configuration',
        variant: 'destructive',
      });
    } finally {
      setLintLoading(false);
    }
  }, [network, buildLintRequest]);

  useEffect(() => {
    if (network) {
      performConfigLint();
    }
  }, [network, performConfigLint]);

  return {
    lintResults,
    lintLoading,
    performConfigLint,
  };
}

function locationToLint(loc: LocationResponse) {
  return {
    name: loc.name,
    description: loc.description ?? undefined,
    external_endpoint: loc.external_endpoint ?? undefined,
  };
}

function deviceToLint(dev: DeviceResponse) {
  return {
    name: dev.name,
    description: dev.description ?? undefined,
    wireguard_ip: dev.wireguard_ip ?? undefined,
    public_key: dev.public_key,
    preshared_key: dev.preshared_key_encrypted,
    enabled: dev.enabled,
  };
}
