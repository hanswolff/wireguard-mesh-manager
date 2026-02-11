'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { AuditEventParams } from '@/lib/api';
import { X } from 'lucide-react';
import { AUDIT_ACTIONS, RESOURCE_TYPES } from '@/constants/audit';

interface AuditFiltersProps {
  filters: AuditEventParams;
  onFilterChange: (
    key: keyof AuditEventParams,
    value: string | number | boolean | undefined
  ) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

export function AuditFilters({
  filters,
  onFilterChange,
  onClearFilters,
  hasActiveFilters,
}: AuditFiltersProps) {
  return (
    <div className="mt-6 p-4 border rounded-lg bg-muted/50 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-medium">Event Filters</h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearFilters}
          disabled={!hasActiveFilters}
        >
          <X className="h-4 w-4 mr-2" />
          Clear Filters
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label htmlFor="actor">Actor</Label>
          <Input
            id="actor"
            placeholder="Filter by actor..."
            value={filters.actor || ''}
            onChange={(e) =>
              onFilterChange('actor', e.target.value || undefined)
            }
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="action">Action</Label>
          <Select
            value={filters.action || ''}
            onValueChange={(value) =>
              onFilterChange('action', value || undefined)
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Select action..." />
            </SelectTrigger>
            <SelectContent>
              {AUDIT_ACTIONS.map((action) => (
                <SelectItem key={action} value={action}>
                  {action}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="resource_type">Resource Type</Label>
          <Select
            value={filters.resource_type || ''}
            onValueChange={(value) =>
              onFilterChange('resource_type', value || undefined)
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Select resource type..." />
            </SelectTrigger>
            <SelectContent>
              {RESOURCE_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="network_id">Network ID</Label>
          <Input
            id="network_id"
            placeholder="Filter by network ID..."
            value={filters.network_id || ''}
            onChange={(e) =>
              onFilterChange('network_id', e.target.value || undefined)
            }
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="start_date">Start Date</Label>
          <Input
            id="start_date"
            type="datetime-local"
            value={filters.start_date || ''}
            onChange={(e) =>
              onFilterChange('start_date', e.target.value || undefined)
            }
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="end_date">End Date</Label>
          <Input
            id="end_date"
            type="datetime-local"
            value={filters.end_date || ''}
            onChange={(e) =>
              onFilterChange('end_date', e.target.value || undefined)
            }
          />
        </div>
      </div>

      <div className="flex gap-2 items-center">
        <Label
          htmlFor="include_details"
          className="flex items-center space-x-2"
        >
          <input
            id="include_details"
            type="checkbox"
            checked={filters.include_details || false}
            onChange={(e) =>
              onFilterChange('include_details', e.target.checked)
            }
          />
          <span>Include event details</span>
        </Label>
      </div>
    </div>
  );
}
