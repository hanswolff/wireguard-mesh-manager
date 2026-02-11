'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Link2,
  Network,
  RefreshCcw,
  Save,
  Trash2,
} from 'lucide-react';
import apiClient, {
  type DevicePeerLink,
  type DevicePeerLinkCreate,
  type DeviceResponse,
  type WireGuardNetworkResponse,
} from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from '@/components/ui/use-toast';
import { useBreadcrumbs } from '@/components/breadcrumb-provider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

type KeepaliveMode = 'inherit' | 'disabled' | 'custom';

type LinkFormState = {
  keepaliveMode: KeepaliveMode;
  keepaliveValue: string;
  customRows: Array<{ key: string; value: string }>;
};

const EMPTY_FORM: LinkFormState = {
  keepaliveMode: 'inherit',
  keepaliveValue: '',
  customRows: [{ key: '', value: '' }],
};

const buildPairKey = (fromId: string, toId: string) => `${fromId}::${toId}`;

const formStateFromProperties = (
  properties: DevicePeerLink['properties']
): LinkFormState => {
  if (!properties) {
    return { ...EMPTY_FORM };
  }

  const keepaliveValue = properties.PersistentKeepalive;
  let keepaliveMode: KeepaliveMode = 'inherit';
  let keepaliveString = '';

  if (Object.prototype.hasOwnProperty.call(properties, 'PersistentKeepalive')) {
    if (keepaliveValue === null || keepaliveValue === undefined) {
      keepaliveMode = 'disabled';
    } else {
      keepaliveMode = 'custom';
      keepaliveString = String(keepaliveValue);
    }
  }

  const customRows = Object.entries(properties)
    .filter(([key]) => key !== 'PersistentKeepalive')
    .map(([key, value]) => ({ key, value: String(value ?? '') }));

  return {
    keepaliveMode,
    keepaliveValue: keepaliveString,
    customRows: customRows.length ? customRows : [{ key: '', value: '' }],
  };
};

const buildPropertiesPayload = (formState: LinkFormState): Record<string, string | number | null> => {
  const properties: Record<string, string | number | null> = {};

  if (formState.keepaliveMode === 'custom') {
    properties.PersistentKeepalive = Number(formState.keepaliveValue);
  } else if (formState.keepaliveMode === 'disabled') {
    properties.PersistentKeepalive = null;
  }

  formState.customRows.forEach((row) => {
    if (row.key.trim()) {
      properties[row.key.trim()] = row.value.trim();
    }
  });

  return properties;
};

const isNumeric = (value: string) => value.trim() !== '' && !Number.isNaN(Number(value));

export default function NetworkConnectionsPage() {
  const params = useParams();
  const router = useRouter();
  const networkId = params.id as string;
  const { setLabel } = useBreadcrumbs();
  const [network, setNetwork] = useState<WireGuardNetworkResponse | null>(null);
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [links, setLinks] = useState<Record<string, DevicePeerLink>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeDeviceId, setActiveDeviceId] = useState<string | null>(null);
  const [selectedPair, setSelectedPair] = useState<{
    a: DeviceResponse;
    b: DeviceResponse;
  } | null>(null);
  const [aToBState, setAToBState] = useState<LinkFormState>({ ...EMPTY_FORM });
  const [bToAState, setBToAState] = useState<LinkFormState>({ ...EMPTY_FORM });
  const [saving, setSaving] = useState<string | null>(null);

  const deviceById = useMemo(() => {
    return devices.reduce<Record<string, DeviceResponse>>((acc, device) => {
      acc[device.id] = device;
      return acc;
    }, {});
  }, [devices]);

  const refreshData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [networkData, devicesData, linksData] = await Promise.all([
        apiClient.getNetwork(networkId),
        apiClient.listDevices({ network_id: networkId }),
        apiClient.listDevicePeerLinks(networkId),
      ]);
      setNetwork(networkData);
      setDevices(
        devicesData
          .filter((device) => device.enabled)
          .sort((a, b) => a.name.localeCompare(b.name))
      );
      const linkMap: Record<string, DevicePeerLink> = {};
      linksData.forEach((link) => {
        linkMap[buildPairKey(link.from_device_id, link.to_device_id)] = link;
      });
      setLinks(linkMap);
      setLabel(`/networks/${networkId}`, networkData.name || networkId);
      setLabel(`/networks/${networkId}/connections`, 'Connections');
    } catch (fetchError) {
      setError(
        fetchError instanceof Error
          ? fetchError.message
          : 'Failed to load connections'
      );
      toast({
        title: 'Error',
        description:
          fetchError instanceof Error
            ? fetchError.message
            : 'Failed to load connections',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (networkId) {
      void refreshData();
    }
  }, [networkId]);

  useEffect(() => {
    if (!selectedPair) {
      setAToBState({ ...EMPTY_FORM });
      setBToAState({ ...EMPTY_FORM });
      return;
    }
    const aToB = links[buildPairKey(selectedPair.a.id, selectedPair.b.id)];
    const bToA = links[buildPairKey(selectedPair.b.id, selectedPair.a.id)];
    setAToBState(formStateFromProperties(aToB?.properties));
    setBToAState(formStateFromProperties(bToA?.properties));
  }, [links, selectedPair]);

  const positions = useMemo(() => {
    const count = devices.length || 1;
    const radius = 40;
    return devices.map((device, index) => {
      const angle = (2 * Math.PI * index) / count - Math.PI / 2;
      return {
        id: device.id,
        x: 50 + radius * Math.cos(angle),
        y: 50 + radius * Math.sin(angle),
      };
    });
  }, [devices]);

  const selectPair = (deviceA: DeviceResponse, deviceB: DeviceResponse) => {
    if (deviceA.id === deviceB.id) {
      return;
    }
    setSelectedPair({ a: deviceA, b: deviceB });
    setActiveDeviceId(null);
  };

  const handleDeviceClick = (device: DeviceResponse) => {
    if (!activeDeviceId) {
      setActiveDeviceId(device.id);
      setSelectedPair(null);
      return;
    }
    if (activeDeviceId === device.id) {
      setActiveDeviceId(null);
      return;
    }
    const activeDevice = deviceById[activeDeviceId];
    if (activeDevice) {
      selectPair(activeDevice, device);
    }
  };

  const handleLineClick = (deviceA: DeviceResponse, deviceB: DeviceResponse) => {
    selectPair(deviceA, deviceB);
  };

  const hasProperties = (fromId: string, toId: string) =>
    Boolean(links[buildPairKey(fromId, toId)]);

  const saveLink = async (
    fromDevice: DeviceResponse,
    toDevice: DeviceResponse,
    state: LinkFormState
  ) => {
    if (state.keepaliveMode === 'custom' && !isNumeric(state.keepaliveValue)) {
      toast({
        title: 'Invalid keepalive value',
        description: 'PersistentKeepalive must be a valid number of seconds.',
        variant: 'destructive',
      });
      return;
    }

    const properties = buildPropertiesPayload(state);
    const payload: DevicePeerLinkCreate = {
      from_device_id: fromDevice.id,
      to_device_id: toDevice.id,
      properties,
    };

    const linkKey = buildPairKey(fromDevice.id, toDevice.id);
    const existing = links[linkKey];

    if (Object.keys(properties).length === 0) {
      if (!existing) {
        toast({
          title: 'Nothing to save',
          description: 'Add properties before saving this direction.',
        });
        return;
      }
      setSaving(linkKey);
      try {
        await apiClient.deleteDevicePeerLink(
          networkId,
          fromDevice.id,
          toDevice.id
        );
        setLinks((prev) => {
          const next = { ...prev };
          delete next[linkKey];
          return next;
        });
        toast({
          title: 'Link cleared',
          description: `${fromDevice.name} → ${toDevice.name} properties removed.`,
        });
      } catch (saveError) {
        toast({
          title: 'Failed to clear link',
          description:
            saveError instanceof Error
              ? saveError.message
              : 'Unable to clear link properties.',
          variant: 'destructive',
        });
      } finally {
        setSaving(null);
      }
      return;
    }

    setSaving(linkKey);
    try {
      const response = await apiClient.upsertDevicePeerLink(networkId, payload);
      setLinks((prev) => ({
        ...prev,
        [linkKey]: response,
      }));
      toast({
        title: 'Link saved',
        description: `${fromDevice.name} → ${toDevice.name} updated.`,
      });
    } catch (saveError) {
      toast({
        title: 'Failed to save link',
        description:
          saveError instanceof Error
            ? saveError.message
            : 'Unable to save link properties.',
        variant: 'destructive',
      });
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div>
            <Skeleton className="h-8 w-[240px]" />
            <Skeleton className="h-4 w-[320px]" />
          </div>
        </div>
        <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
          <Skeleton className="h-[520px]" />
          <Skeleton className="h-[520px]" />
        </div>
      </div>
    );
  }

  if (error || !network) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {error || 'Network not found.'}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push(`/networks/${networkId}`)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Network
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <Network className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-semibold">{network.name}</h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Define per-device peer properties for this mesh.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href={`/networks/${networkId}`}>
            <Button variant="outline">Overview</Button>
          </Link>
          <Button variant="outline" onClick={refreshData}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <Card className="relative overflow-hidden">
          <CardHeader className="border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Link2 className="h-5 w-5 text-primary" />
                Device Mesh
              </CardTitle>
              <Badge variant="secondary">
                {devices.length} devices enabled
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="relative h-[520px]">
            <div className="absolute inset-6 rounded-full bg-gradient-to-br from-slate-50 via-white to-slate-100 shadow-inner" />
            <svg
              className="absolute inset-0 h-full w-full"
              viewBox="0 0 100 100"
            >
              {devices.map((deviceA, index) =>
                devices.slice(index + 1).map((deviceB) => {
                  const posA = positions.find((p) => p.id === deviceA.id);
                  const posB = positions.find((p) => p.id === deviceB.id);
                  if (!posA || !posB) {
                    return null;
                  }
                  const pairActive =
                    selectedPair &&
                    ((selectedPair.a.id === deviceA.id &&
                      selectedPair.b.id === deviceB.id) ||
                      (selectedPair.a.id === deviceB.id &&
                        selectedPair.b.id === deviceA.id));
                  const hasAny =
                    hasProperties(deviceA.id, deviceB.id) ||
                    hasProperties(deviceB.id, deviceA.id);
                  return (
                    <line
                      key={`${deviceA.id}-${deviceB.id}`}
                      x1={posA.x}
                      y1={posA.y}
                      x2={posB.x}
                      y2={posB.y}
                      stroke={pairActive ? '#0f172a' : hasAny ? '#64748b' : '#cbd5f5'}
                      strokeWidth={pairActive ? 0.6 : hasAny ? 0.4 : 0.25}
                      strokeDasharray={hasAny ? '0' : '1 2'}
                      onClick={() => handleLineClick(deviceA, deviceB)}
                      className="cursor-pointer transition-colors"
                    />
                  );
                })
              )}
            </svg>
            {devices.map((device, index) => {
              const position = positions[index];
              const isActive = activeDeviceId === device.id;
              const isSelected =
                selectedPair &&
                (selectedPair.a.id === device.id ||
                  selectedPair.b.id === device.id);
              return (
                <button
                  key={device.id}
                  type="button"
                  onClick={() => handleDeviceClick(device)}
                  className={`absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center rounded-full border px-4 py-2 text-xs shadow-sm transition ${
                    isSelected
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : isActive
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                  }`}
                  style={{ left: `${position.x}%`, top: `${position.y}%` }}
                >
                  <span className="font-semibold">{device.name}</span>
                  <span className="text-[10px] opacity-70">
                    {device.wireguard_ip || 'No IP'}
                  </span>
                </button>
              );
            })}
            <div className="absolute bottom-6 left-6 rounded-lg border border-dashed border-slate-200 bg-white/70 px-4 py-2 text-xs text-slate-600">
              Click a device, then another to open a connection editor.
            </div>
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardHeader className="border-b">
            <CardTitle>Connection Editor</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            {!selectedPair ? (
              <div className="space-y-4 text-sm text-muted-foreground">
                <p>Select a connection to edit per-direction properties.</p>
                <div className="rounded-lg border border-dashed border-slate-200 p-4 text-xs text-slate-600">
                  Directional rules apply: A → B can differ from B → A.
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {[{
                  from: selectedPair.a,
                  to: selectedPair.b,
                  state: aToBState,
                  setState: setAToBState,
                }, {
                  from: selectedPair.b,
                  to: selectedPair.a,
                  state: bToAState,
                  setState: setBToAState,
                }].map(({ from, to, state, setState }) => {
                  const linkKey = buildPairKey(from.id, to.id);
                  return (
                    <div key={linkKey} className="space-y-4 rounded-lg border p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold">
                            {from.name} → {to.name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {from.location_name || 'Unknown location'} to{' '}
                            {to.location_name || 'Unknown location'}
                          </p>
                        </div>
                        {hasProperties(from.id, to.id) ? (
                          <Badge variant="secondary">Configured</Badge>
                        ) : (
                          <Badge variant="outline">Default</Badge>
                        )}
                      </div>

                      <div className="space-y-2">
                        <label className="text-xs font-medium">
                          PersistentKeepalive
                        </label>
                        <div className="flex items-center gap-2">
                          <Select
                            value={state.keepaliveMode}
                            onValueChange={(value) =>
                              setState((prev) => ({
                                ...prev,
                                keepaliveMode: value as KeepaliveMode,
                              }))
                            }
                          >
                            <SelectTrigger className="w-[140px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="inherit">Inherit</SelectItem>
                              <SelectItem value="disabled">Disabled</SelectItem>
                              <SelectItem value="custom">Custom</SelectItem>
                            </SelectContent>
                          </Select>
                          <Input
                            type="number"
                            min={0}
                            max={86400}
                            disabled={state.keepaliveMode !== 'custom'}
                            placeholder={`Default (${network.persistent_keepalive ?? 'off'})`}
                            value={state.keepaliveValue}
                            onChange={(event) =>
                              setState((prev) => ({
                                ...prev,
                                keepaliveValue: event.target.value,
                              }))
                            }
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-medium">
                            Custom properties
                          </label>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setState((prev) => ({
                                ...prev,
                                customRows: [
                                  ...prev.customRows,
                                  { key: '', value: '' },
                                ],
                              }))
                            }
                          >
                            Add row
                          </Button>
                        </div>
                        <div className="space-y-2">
                          {state.customRows.map((row, index) => (
                            <div key={`${index}-${row.key}`} className="flex gap-2">
                              <Input
                                placeholder="Key"
                                value={row.key}
                                onChange={(event) => {
                                  const value = event.target.value;
                                  setState((prev) => {
                                    const nextRows = [...prev.customRows];
                                    nextRows[index] = { ...row, key: value };
                                    return { ...prev, customRows: nextRows };
                                  });
                                }}
                              />
                              <Input
                                placeholder="Value"
                                value={row.value}
                                onChange={(event) => {
                                  const value = event.target.value;
                                  setState((prev) => {
                                    const nextRows = [...prev.customRows];
                                    nextRows[index] = { ...row, value };
                                    return { ...prev, customRows: nextRows };
                                  });
                                }}
                              />
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                onClick={() =>
                                  setState((prev) => ({
                                    ...prev,
                                    customRows: prev.customRows.filter(
                                      (_, rowIndex) => rowIndex !== index
                                    ),
                                  }))
                                }
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <Button
                          type="button"
                          onClick={() => saveLink(from, to, state)}
                          disabled={saving === linkKey}
                        >
                          <Save className="mr-2 h-4 w-4" />
                          Save
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => {
                            setState(
                              formStateFromProperties(
                                links[buildPairKey(from.id, to.id)]?.properties
                              )
                            );
                          }}
                          disabled={saving === linkKey}
                        >
                          Reset
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
