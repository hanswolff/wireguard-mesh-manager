import { WireGuardNetworkResponse } from '@/lib/api-client';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import {
  MapPin,
  Cpu,
  SortAsc,
  SortDesc,
  MoreHorizontal,
  Edit,
  Trash2,
  Eye,
  Globe,
} from 'lucide-react';
import Link from 'next/link';
import { SortDirection } from '@/lib/utils/sorting';
import { NetworkSortField } from '@/lib/constants/networks';

interface NetworkTableProps {
  networks: WireGuardNetworkResponse[];
  sortField: NetworkSortField;
  sortDirection: SortDirection;
  onSort: (field: NetworkSortField) => void;
  onEdit: (network: WireGuardNetworkResponse) => void;
  onDelete: (network: WireGuardNetworkResponse) => void;
}

function getSortIcon(
  field: NetworkSortField,
  currentField: NetworkSortField,
  direction: SortDirection
) {
  return field === currentField ? (
    direction === 'asc' ? (
      <SortAsc className="h-4 w-4" />
    ) : (
      <SortDesc className="h-4 w-4" />
    )
  ) : (
    <SortAsc className="h-4 w-4" />
  );
}

export function NetworkTable({
  networks,
  sortField,
  sortDirection,
  onSort,
  onEdit,
  onDelete,
}: NetworkTableProps) {
  if (networks.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <Globe className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No networks found</h3>
          <p className="text-muted-foreground">
            Get started by creating your first network
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Networks ({networks.length})</CardTitle>
        <CardDescription>
          Manage your WireGuard networks and their configurations
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onSort('name')}
              >
                <div className="flex items-center space-x-1">
                  <span>Name</span>
                  {getSortIcon('name', sortField, sortDirection)}
                </div>
              </TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Network CIDR</TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onSort('location_count')}
              >
                <div className="flex items-center space-x-1">
                  <MapPin className="h-4 w-4" />
                  <span>Locations</span>
                  {getSortIcon('location_count', sortField, sortDirection)}
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onSort('device_count')}
              >
                <div className="flex items-center space-x-1">
                  <Cpu className="h-4 w-4" />
                  <span>Devices</span>
                  {getSortIcon('device_count', sortField, sortDirection)}
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onSort('created_at')}
              >
                <div className="flex items-center space-x-1">
                  <span>Created</span>
                  {getSortIcon('created_at', sortField, sortDirection)}
                </div>
              </TableHead>
              <TableHead className="w-[70px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {networks.map((network) => (
              <TableRow key={network.id} className="hover:bg-muted/50">
                <TableCell>
                  <div>
                    <Link
                      href={`/networks/${network.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {network.name}
                    </Link>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="max-w-[200px] truncate">
                    {network.description || (
                      <span className="text-muted-foreground">
                        No description
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <code className="text-sm bg-muted px-2 py-1 rounded">
                    {network.network_cidr}
                  </code>
                </TableCell>
                <TableCell>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">
                      {network.location_count}
                    </span>
                    <span className="text-muted-foreground text-sm">
                      locations
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{network.device_count}</span>
                    <span className="text-muted-foreground text-sm">
                      devices
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="text-sm text-muted-foreground">
                    {new Date(network.created_at).toLocaleDateString()}
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
                        <Link href={`/networks/${network.id}`}>
                          <Eye className="h-4 w-4 mr-2" />
                          View Details
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onEdit(network)}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => onDelete(network)}
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
      </CardContent>
    </Card>
  );
}
