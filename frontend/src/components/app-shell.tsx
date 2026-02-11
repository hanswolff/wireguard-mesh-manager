'use client';

import { useState } from 'react';
import { Sidebar } from './sidebar';
import { Topbar } from './topbar';
import { Breadcrumbs } from './breadcrumbs';
import { BreadcrumbProvider } from './breadcrumb-provider';
import { LockedPlaceholder } from './locked-placeholder';

interface AppShellProps {
  children: React.ReactNode;
  showBreadcrumbs?: boolean;
}

const APP_VERSION = '1.0.0';

export function AppShell({ children, showBreadcrumbs = true }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <BreadcrumbProvider>
      <div className="flex h-screen bg-background">
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} version={APP_VERSION} />

        <div className="flex-1 flex flex-col min-w-0">
          <Topbar onMenuToggle={() => setSidebarOpen(true)} />
          {showBreadcrumbs && <Breadcrumbs />}
          <main className="flex-1 overflow-y-auto p-6">
            <LockedPlaceholder>
              {children}
            </LockedPlaceholder>
          </main>
        </div>
      </div>
    </BreadcrumbProvider>
  );
}
