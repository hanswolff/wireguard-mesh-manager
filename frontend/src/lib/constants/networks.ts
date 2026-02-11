export const NETWORK_SORT_FIELDS = [
  'name',
  'created_at',
  'updated_at',
  'device_count',
  'location_count',
] as const;

export type NetworkSortField = (typeof NETWORK_SORT_FIELDS)[number];
