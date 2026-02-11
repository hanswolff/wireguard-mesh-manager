'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Shield, Activity, Settings, Globe, Users, Key } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: Activity },
  { name: 'Networks', href: '/networks', icon: Globe },
  { name: 'Devices', href: '/devices', icon: Users },
  { name: 'Audit Events', href: '/audit', icon: Shield },
  { name: 'Key Rotation', href: '/key-rotation', icon: Key },
  { name: 'Settings', href: '/settings', icon: Settings },
];

interface NavigationProps {
  variant?: 'sidebar' | 'topbar';
}

export function Navigation({ variant = 'sidebar' }: NavigationProps) {
  const pathname = usePathname();

  if (variant === 'topbar') {
    return (
      <nav className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-6">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-8">
              <div className="flex items-center space-x-2">
                <Shield className="h-8 w-8" />
                <span className="text-xl font-bold">WireGuard Mesh Manager</span>
              </div>
              <div className="hidden md:flex items-center space-x-6">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-md transition-colors',
                        pathname === item.href
                          ? 'text-foreground bg-accent'
                          : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="space-y-1 px-3">
      {navigation.map((item) => {
        const Icon = item.icon;
        return (
          <Link
            key={item.name}
            href={item.href}
            className={cn(
              'flex items-center space-x-3 px-3 py-2 text-sm font-medium rounded-md transition-colors',
              pathname === item.href
                ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{item.name}</span>
          </Link>
        );
      })}
    </nav>
  );
}
