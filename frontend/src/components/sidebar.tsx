'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { getContrastColor } from '@/lib/utils/color-utils';
import { X, Edit3 } from 'lucide-react';
import { Navigation } from './navigation';
import { AboutDialog } from './about-dialog';
import { LogoEditDialog } from './logo-edit-dialog';
import { apiClient, OperationalSettingsResponse } from '@/lib/api-client';
import { useUnlock } from '@/contexts/unlock-context';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  version?: string;
}

export function Sidebar({ open, onClose, version = '1.0.0' }: SidebarProps) {
  const { isUnlocked } = useUnlock();
  const [settings, setSettings] = useState<OperationalSettingsResponse | null>(null);
  const [showLogoEdit, setShowLogoEdit] = useState(false);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await apiClient.getOperationalSettings();
        setSettings(data);
      } catch (error) {
        console.error('Failed to load operational settings:', error);
      }
    };

    loadSettings();
  }, []);

  const logoBgColor = settings?.logo_bg_color;
  const logoText = settings?.logo_text || 'WG';
  const hasCustomLogo = logoBgColor || logoText !== 'WG';

  const logoTextColor = logoBgColor
    ? getContrastColor(logoBgColor)
    : 'hsl(var(--sidebar-primary-foreground))';

  return (
    <>
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-sidebar-border transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center justify-between px-6 border-b border-sidebar-border">
            <div className="flex items-center space-x-2">
              <button
                className="relative group"
                onClick={() => isUnlocked && setShowLogoEdit(true)}
                aria-label={isUnlocked ? "Edit logo" : "Unlock to edit logo"}
              >
                <div
                  className="h-8 w-8 rounded-md flex items-center justify-center transition-colors"
                  style={{
                    backgroundColor: logoBgColor || 'hsl(var(--sidebar-primary))',
                  }}
                >
                  <span
                    className="font-bold text-sm"
                    style={{ color: logoTextColor }}
                  >
                    {logoText}
                  </span>
                </div>
                {isUnlocked && (
                  <div className="absolute inset-0 rounded-md bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <Edit3 className="h-4 w-4 text-white" />
                  </div>
                )}
              </button>
              <span className="text-sidebar-foreground font-semibold text-sm">
                {settings?.app_name || 'WireGuard Mesh Manager'}
              </span>
            </div>
            <button
              className="lg:hidden p-1 rounded-md hover:bg-sidebar-accent transition-colors"
              onClick={onClose}
            >
              <X className="h-5 w-5 text-sidebar-foreground" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-4">
            <Navigation />
          </div>

          <div className="border-t border-sidebar-border p-3">
            <AboutDialog version={version} />
          </div>
        </div>
      </div>

      {settings && (
        <LogoEditDialog
          open={showLogoEdit}
          onOpenChange={setShowLogoEdit}
          settings={settings}
          onSave={() => {
            apiClient.getOperationalSettings().then(setSettings);
          }}
        />
      )}
    </>
  );
}
