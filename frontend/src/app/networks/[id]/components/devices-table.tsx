'use client';

import {
  Edit,
  Trash2,
  MoreHorizontal,
  Key,
  SortAsc,
  SortDesc,
  ExternalLink,
  Eye,
  RefreshCw,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { type DeviceResponse } from '@/lib/api-client';
import { type SortField, type SortDirection } from './device-filters';
import Link from 'next/link';

interface SortableHeaderProps {
  field: SortField;
  children: React.ReactNode;
  onSort: (field: SortField) => void;
  sortField: SortField;
  sortDirection: SortDirection;
}

function SortableHeader({
  field,
  children,
  onSort,
  sortField,
  sortDirection,
}: SortableHeaderProps) {
  return (
    <TableHead
      className="cursor-pointer hover:bg-muted/50"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center space-x-1">
        <span>{children}</span>
        {sortField === field &&
          (sortDirection === 'asc' ? (
            <SortAsc className="h-4 w-4" />
          ) : (
            <SortDesc className="h-4 w-4" />
          ))}
      </div>
    </TableHead>
  );
}

interface DevicesTableProps {
  devices: DeviceResponse[];
  networkId: string;
  onEditDevice: (device: DeviceResponse) => void;
  onDeleteDevice: (device: DeviceResponse) => void;
  onRegenerateApiKey: (device: DeviceResponse) => void;
  onRegenerateKeys: (device: DeviceResponse) => void;
  onSort: (field: SortField) => void;
  sortField: SortField;
  sortDirection: SortDirection;
}

export default function DevicesTable({
  devices,
  networkId,
  onEditDevice,
  onDeleteDevice,
  onRegenerateApiKey,
  onRegenerateKeys,
  onSort,
  sortField,
  sortDirection,
}: DevicesTableProps) {
  if (devices.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="text-lg font-semibold mb-2">No devices found</div>
        <div className="text-muted-foreground">
          Try adjusting your filters or add your first device
        </div>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <SortableHeader
            field="name"
            onSort={onSort}
            sortField={sortField}
            sortDirection={sortDirection}
          >
            Name
          </SortableHeader>
          <TableHead>Status</TableHead>
          <SortableHeader
            field="location_name"
            onSort={onSort}
            sortField={sortField}
            sortDirection={sortDirection}
          >
            Location
          </SortableHeader>
          <SortableHeader
            field="wireguard_ip"
            onSort={onSort}
            sortField={sortField}
            sortDirection={sortDirection}
          >
            WireGuard IP
          </SortableHeader>
          <TableHead>API Key</TableHead>
          <SortableHeader
            field="created_at"
            onSort={onSort}
            sortField={sortField}
            sortDirection={sortDirection}
          >
            Created
          </SortableHeader>
          <TableHead className="w-[70px]" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {devices.map((device) => (
          <TableRow key={device.id}>
            <TableCell className="font-medium">
              <div>
                <Link
                  href={`/networks/${networkId}/devices/${device.id}`}
                  className="hover:text-primary flex items-center gap-1 hover:underline"
                >
                  {device.name}
                  <ExternalLink className="h-3 w-3" />
                </Link>
                {device.description && (
                  <div className="text-sm text-muted-foreground truncate max-w-[200px]">
                    {device.description}
                  </div>
                )}
              </div>
            </TableCell>
            <TableCell>
              <Badge variant={device.enabled ? 'default' : 'secondary'}>
                {device.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge variant="outline">{device.location_name}</Badge>
            </TableCell>
            <TableCell>
              {device.wireguard_ip ? (
                <code className="text-sm bg-muted px-2 py-1 rounded">
                  {device.wireguard_ip}
                </code>
              ) : (
                <Badge variant="outline">Not assigned</Badge>
              )}
            </TableCell>
            <TableCell>
              {device.api_key ? (
                <div className="flex items-center space-x-2">
                  <Badge variant="secondary" className="text-xs">
                    <Key className="h-3 w-3 mr-1" />
                    Generated
                  </Badge>
                  {device.api_key_last_used && (
                    <span className="text-xs text-muted-foreground">
                      Used{' '}
                      {new Date(device.api_key_last_used).toLocaleDateString()}
                    </span>
                  )}
                </div>
              ) : (
                <Badge variant="outline">None</Badge>
              )}
            </TableCell>
            <TableCell>
              <div className="text-sm text-muted-foreground">
                {new Date(device.created_at).toLocaleDateString()}
              </div>
            </TableCell>
            <TableCell>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem asChild>
                    <Link href={`/networks/${networkId}/devices/${device.id}`}>
                      <Eye className="h-4 w-4 mr-2" />
                      View Details
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onEditDevice(device)}>
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onRegenerateApiKey(device)}>
                    <Key className="h-4 w-4 mr-2" />
                    Regenerate API Key
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onRegenerateKeys(device)}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Regenerate WireGuard Keys
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onDeleteDevice(device)}
                    className="text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
