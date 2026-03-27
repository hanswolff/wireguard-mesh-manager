'use client';

import { useState } from 'react';
import { Menu } from 'lucide-react';
import { ThemeToggle } from './theme-toggle';
import { MasterPasswordUnlockModal } from './ui/master-password-unlock-modal';
import { UnlockStatusButton } from './ui/unlock-status-button';
import { useUnlock } from '@/contexts/unlock-context';

interface TopbarProps {
  onMenuToggle: () => void;
}

export function Topbar({ onMenuToggle }: TopbarProps) {
  const { showUnlockModalFlag, hideUnlockModal } = useUnlock();
  const [showUnlockModal, setShowUnlockModal] = useState(false);

  return (
    <>
      <header className="h-16 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex h-full items-center justify-between px-4 lg:px-6">
          <div className="flex items-center space-x-4">
            <button
              className="lg:hidden p-2 rounded-md hover:bg-accent transition-colors"
              onClick={onMenuToggle}
            >
              <Menu className="h-5 w-5" />
            </button>
          </div>

          <div className="flex items-center space-x-4">
            <UnlockStatusButton />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Global unlock modal (triggered by showUnlockModal from context) */}
      <MasterPasswordUnlockModal
        isOpen={showUnlockModalFlag}
        onClose={hideUnlockModal}
      />

      {/* Local unlock modal (triggered by clicking the button in topbar) */}
      <MasterPasswordUnlockModal
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
      />
    </>
  );
}
