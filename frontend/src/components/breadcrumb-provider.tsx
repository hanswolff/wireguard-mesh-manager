'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface BreadcrumbContextType {
  labels: Record<string, string>;
  setLabel: (path: string, label: string) => void;
  clearLabels: () => void;
}

const BreadcrumbContext = createContext<BreadcrumbContextType | undefined>(
  undefined
);

export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [labels, setLabels] = useState<Record<string, string>>({});

  const setLabel = (path: string, label: string) => {
    setLabels((prev) => ({ ...prev, [path]: label }));
  };

  const clearLabels = () => {
    setLabels({});
  };

  return (
    <BreadcrumbContext.Provider value={{ labels, setLabel, clearLabels }}>
      {children}
    </BreadcrumbContext.Provider>
  );
}

export function useBreadcrumbs() {
  const context = useContext(BreadcrumbContext);
  if (context === undefined) {
    throw new Error('useBreadcrumbs must be used within a BreadcrumbProvider');
  }
  return context;
}
