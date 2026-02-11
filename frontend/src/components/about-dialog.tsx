'use client';

import { Info } from 'lucide-react';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface AboutDialogProps {
  version: string;
}

export function AboutDialog({ version }: AboutDialogProps) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          className="w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          <Info className="h-4 w-4 mr-3" />
          About
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>WireGuard Mesh Manager</DialogTitle>
          <DialogDescription>
            A secret-management and configuration-deployment tool for WireGuard-based infrastructure
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <p className="text-sm font-medium">Version</p>
            <p className="text-sm text-muted-foreground">{version}</p>
          </div>
          <div>
            <p className="text-sm font-medium">License</p>
            <p className="text-sm text-muted-foreground">Apache License 2.0</p>
          </div>
          <div>
            <p className="text-sm font-medium">Copyright</p>
            <p className="text-sm text-muted-foreground">© 2025 Hans Wolff</p>
          </div>
          <div>
            <p className="text-sm font-medium">Source Code</p>
            <a
              href="https://github.com/hanswolff/wireguard-mesh-manager"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline"
            >
              github.com/hanswolff/wireguard-mesh-manager
            </a>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
