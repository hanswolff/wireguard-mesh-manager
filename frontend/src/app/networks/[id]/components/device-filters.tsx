'use client';

import { Search, Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { type LocationResponse } from '@/lib/api-client';

export type SortField =
  | 'name'
  | 'created_at'
  | 'location_name'
  | 'wireguard_ip';
export type SortDirection = 'asc' | 'desc';
export type EnabledFilter = 'all' | 'true' | 'false';

interface DeviceFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  locationFilter: string;
  onLocationChange: (value: string) => void;
  enabledFilter: EnabledFilter;
  onEnabledChange: (value: EnabledFilter) => void;
  sortField: SortField;
  sortDirection: SortDirection;
  onSortChange: (field: SortField) => void;
  showFilters: boolean;
  onShowFiltersChange: (show: boolean) => void;
  onClearFilters: () => void;
  locations: LocationResponse[];
}

const sortOptions = [
  { value: 'name-asc', label: 'Name (A-Z)' },
  { value: 'name-desc', label: 'Name (Z-A)' },
  { value: 'location_name-asc', label: 'Location (A-Z)' },
  { value: 'location_name-desc', label: 'Location (Z-A)' },
  { value: 'created_at-asc', label: 'Created (oldest)' },
  { value: 'created_at-desc', label: 'Created (newest)' },
  { value: 'wireguard_ip-asc', label: 'IP (ascending)' },
  { value: 'wireguard_ip-desc', label: 'IP (descending)' },
];

function DeviceFilters({
  searchQuery,
  onSearchChange,
  locationFilter,
  onLocationChange,
  enabledFilter,
  onEnabledChange,
  sortField,
  sortDirection,
  onSortChange,
  showFilters,
  onShowFiltersChange,
  onClearFilters,
  locations,
}: DeviceFiltersProps) {
  const hasActiveFilters =
    searchQuery || locationFilter !== 'all' || enabledFilter !== 'all';
  const activeFilterCount = [locationFilter !== 'all', enabledFilter !== 'all'].filter(
    Boolean
  ).length;

  const handleSortChange = (value: string) => {
    const [field] = value.split('-') as [SortField, SortDirection];
    onSortChange(field);
  };

  return (
    <div className="flex flex-col space-y-2">
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search devices..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => onShowFiltersChange(!showFilters)}
          className="flex items-center space-x-1"
        >
          <Filter className="h-4 w-4" />
          <span>Filters</span>
          {hasActiveFilters && (
            <Badge
              variant="secondary"
              className="ml-1 h-5 w-5 rounded-full p-0 text-xs"
            >
              {activeFilterCount}
            </Badge>
          )}
        </Button>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearFilters}
            className="flex items-center space-x-1"
          >
            <X className="h-4 w-4" />
            <span>Clear</span>
          </Button>
        )}
      </div>

      {showFilters && (
        <div className="flex flex-col sm:flex-row gap-2 p-3 bg-muted/50 rounded-lg">
          <Select value={locationFilter} onValueChange={onLocationChange}>
            <SelectTrigger className="w-full sm:w-[200px]">
              <SelectValue placeholder="Filter by location" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All locations</SelectItem>
              {locations.map((location) => (
                <SelectItem key={location.id} value={location.id}>
                  {location.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={enabledFilter}
            onValueChange={(value: EnabledFilter) => onEnabledChange(value)}
          >
            <SelectTrigger className="w-full sm:w-[150px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              <SelectItem value="true">Enabled</SelectItem>
              <SelectItem value="false">Disabled</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={`${sortField}-${sortDirection}`}
            onValueChange={handleSortChange}
          >
            <SelectTrigger className="w-full sm:w-[150px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              {sortOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}

export default DeviceFilters;
