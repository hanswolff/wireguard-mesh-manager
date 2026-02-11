'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  MapPin,
  Cpu,
  Globe,
  Edit,
  Download,
  Link2,
  AlertTriangle,
  Shield,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/components/ui/use-toast';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient, { type WireGuardNetworkResponse } from '@/lib/api-client';
import Link from 'next/link';
import { useConfigLint } from '@/hooks/use-config-lint';
import { ConfigLintStatus } from '@/components/networks/config-lint-status';
import NetworkLocations from './components/network-locations';
import NetworkDevices from './components/network-devices';
import { useBreadcrumbs } from '@/components/breadcrumb-provider';

export default function NetworkDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [network, setNetwork] = useState<WireGuardNetworkResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [peerPropertiesCount, setPeerPropertiesCount] = useState(0);
  const [activeTab, setActiveTab] = useState('locations');
  const { setLabel } = useBreadcrumbs();

  const { lintResults, lintLoading, performConfigLint } =
    useConfigLint(network);

  useEffect(() => {
    // Load saved tab from localStorage
    const savedTab = localStorage.getItem(`network-tab-${params.id}`);
    if (savedTab === 'locations' || savedTab === 'devices') {
      setActiveTab(savedTab);
    }
  }, [params.id]);

  useEffect(() => {
    // Save active tab to localStorage
    if (params.id) {
      localStorage.setItem(`network-tab-${params.id}`, activeTab);
    }
  }, [activeTab, params.id]);

  useEffect(() => {
    if (params.id) {
      fetchNetwork(params.id as string);
    }
  }, [params.id]);

  const fetchNetwork = async (networkId: string) => {
    try {
      setLoading(true);
      setError(null);
      const [data, peerLinks] = await Promise.all([
        apiClient.getNetwork(networkId),
        apiClient.listDevicePeerLinks(networkId),
      ]);
      setNetwork(data);
      setPeerPropertiesCount(peerLinks.length);
      const networkName = data.name || networkId;
      // Set breadcrumb label for the network and devices pages
      setLabel(`/networks/${networkId}`, networkName);
      setLabel(`/networks/${networkId}/devices`, 'Devices');
      setLabel(`/networks/${networkId}/connections`, 'Connections');
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : 'Failed to fetch network details'
      );
      toast({
        title: 'Error',
        description:
          error instanceof Error
            ? error.message
            : 'Failed to fetch network details',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Skeleton className="h-10 w-10" />
          <div>
            <Skeleton className="h-8 w-[200px]" />
            <Skeleton className="h-4 w-[300px]" />
          </div>
        </div>
        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-[150px]" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Skeleton className="h-4 w-[100px]" />
                <Skeleton className="h-4 w-[150px]" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (error || !network) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error || 'Network not found'}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={() => router.push('/networks')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Networks
          </Button>
          <div className="flex items-center space-x-3">
            <Globe className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold">{network.name}</h1>
              <p className="text-muted-foreground">
                {network.description || 'No description provided'}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Link href={`/networks/${network.id}/edit`}>
            <Button variant="outline">
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
          </Link>
          <Link href={`/networks/${network.id}/connections`}>
            <Button variant="outline">
              <Link2 className="h-4 w-4 mr-2" />
              Connections
            </Button>
          </Link>
          <Link href={`/networks/${network.id}/export`}>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Export Configs
            </Button>
          </Link>
        </div>
      </div>

      {/* Network Overview */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Network CIDR</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {network.network_cidr}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Locations</CardTitle>
            <MapPin className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{network.location_count}</div>
            <p className="text-xs text-muted-foreground">network endpoints</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Peer Properties
            </CardTitle>
            <Link2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{peerPropertiesCount}</div>
            <p className="text-xs text-muted-foreground">directional links</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Devices</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{network.device_count}</div>
            <p className="text-xs text-muted-foreground">connected devices</p>
          </CardContent>
        </Card>
      </div>

      {/* Network Configuration Details */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <span>Network Configuration</span>
          </CardTitle>
          <CardDescription>
            Detailed configuration settings for this WireGuard network
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Network CIDR
              </h4>
              <code className="text-sm bg-muted px-2 py-1 rounded">
                {network.network_cidr}
              </code>
            </div>
            {network.dns_servers && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">
                  DNS Servers
                </h4>
                <code className="text-sm bg-muted px-2 py-1 rounded">
                  {network.dns_servers}
                </code>
              </div>
            )}
            {network.mtu && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">
                  MTU
                </h4>
                <Badge variant="outline">{network.mtu}</Badge>
              </div>
            )}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Created
              </h4>
              <p className="text-sm">
                {new Date(network.created_at).toLocaleString()}
              </p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Last Updated
              </h4>
              <p className="text-sm">
                {new Date(network.updated_at).toLocaleString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <ConfigLintStatus
        lintResults={lintResults}
        lintLoading={lintLoading}
        onRefresh={performConfigLint}
      />

      {/* Locations and Devices Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="locations">
            <MapPin className="h-4 w-4 mr-2" />
            Locations ({network.location_count})
          </TabsTrigger>
          <TabsTrigger value="devices">
            <Cpu className="h-4 w-4 mr-2" />
            Devices ({network.device_count})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="locations">
          <NetworkLocations networkId={network.id} onLocationChanged={() => fetchNetwork(network.id)} />
        </TabsContent>

        <TabsContent value="devices">
          <NetworkDevices networkId={network.id} onDeviceChanged={() => fetchNetwork(network.id)} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
