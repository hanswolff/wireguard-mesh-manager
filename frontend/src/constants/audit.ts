export const AUDIT_ACTIONS = [
  'CREATE',
  'UPDATE',
  'DELETE',
  'LOGIN',
  'LOGOUT',
  'CONFIG_RETRIEVAL',
  'AUDIT_EXPORT',
  'AUDIT_DOWNLOAD',
  'AUDIT_CLEANUP',
  'API_KEY_GENERATED', // pragma: allowlist secret
  'API_KEY_REVOKED', // pragma: allowlist secret
  'NETWORK_CREATED',
  'NETWORK_UPDATED',
  'DEVICE_ADDED',
  'DEVICE_REMOVED',
  'LOCATION_ADDED',
  'LOCATION_REMOVED',
] as const;

export const RESOURCE_TYPES = [
  'network',
  'device',
  'api_key', // pragma: allowlist secret
  'location',
  'audit_events',
  'user',
] as const;

export const ACTION_COLOR_MAP: Record<
  string,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  CREATE: 'default',
  API_KEY_GENERATED: 'default', // pragma: allowlist secret
  DEVICE_ADDED: 'default',
  LOCATION_ADDED: 'default',
  NETWORK_CREATED: 'default',
  UPDATE: 'secondary',
  NETWORK_UPDATED: 'secondary',
  DELETE: 'destructive',
  DEVICE_REMOVED: 'destructive',
  LOCATION_REMOVED: 'destructive',
  API_KEY_REVOKED: 'destructive', // pragma: allowlist secret
  CONFIG_RETRIEVAL: 'outline',
  AUDIT_EXPORT: 'outline',
  AUDIT_DOWNLOAD: 'outline',
};

export const getActionColor = (
  action: string
): 'default' | 'secondary' | 'destructive' | 'outline' => {
  return ACTION_COLOR_MAP[action] || 'secondary';
};
