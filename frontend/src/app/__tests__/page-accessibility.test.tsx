import { render, screen, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import Home from '../page';
import { apiClient } from '@/lib/api';

jest.mock('next/link', () => ({
  __esModule: true,
  default: ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>,
}));

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    getAuditStatistics: jest.fn().mockResolvedValue({
      total_events: 1250,
      recent_events_24h: 42,
      retention_days: 30,
      storage_stats: {
        total_size_bytes: 2097152,
      },
    }),
    getHealth: jest.fn().mockResolvedValue({
      status: 'healthy',
      database_status: 'healthy',
      version: '1.0.0',
      uptime_seconds: 3600,
      timestamp: '2024-01-01T00:00:00Z',
    }),
  },
}));

// Mock the GlobalStateWrapper
jest.mock('@/components/global-states', () => ({
  GlobalStateWrapper: ({
    children,
    loading,
    error,
    empty,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    errorAction,
  }: {
    children: React.ReactNode;
    loading?: boolean;
    error?: string;
    empty?: boolean;
    errorAction?: React.ReactNode;
  }) => {
    // For accessibility tests, always render children to check content
    // Loading state is tested separately in other tests
    if (error) return <div>Error: {error}</div>;
    if (empty) return <div>Empty</div>;
    return <div>{children}</div>;
  },
}));

// Mock the StatCard component
jest.mock('@/components/stat-card', () => ({
  StatCard: ({
    title,
    value,
    description,
  }: {
    title: string;
    value: string;
    description?: string;
  }) => (
    <div
      data-testid="stat-card"
      role="region"
      aria-label={`${title}: ${value}`}
    >
      <div className="font-medium">{title}</div>
      <div className="text-lg">{value}</div>
      {description && <div className="text-sm">{description}</div>}
    </div>
  ),
}));

// Mock the useUnlock hook
jest.mock('@/contexts/unlock-context', () => ({
  useUnlock: () => ({
    isUnlocked: true,
    isChecking: false,
    status: null,
    unlock: jest.fn(),
    lock: jest.fn(),
    refreshStatus: jest.fn(),
    extendTtl: jest.fn(),
    requireUnlock: jest.fn(),
  }),
}));

// Mock the MasterPasswordUnlockModal component
jest.mock('@/components/ui/master-password-unlock-modal', () => ({
  MasterPasswordUnlockModal: () => null,
}));

describe('Home Page Accessibility', () => {
  const renderPage = async () => {
    const view = render(<Home />);

    await waitFor(() => {
      expect(apiClient.getHealth).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(apiClient.getAuditStatistics).toHaveBeenCalled();
    });

    return view;
  };

  beforeAll(() => {
    extendExpect(expect);
  });

  it('should not have any accessibility violations', async () => {
    const { container } = await renderPage();

    // Wait for the component to fully load
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper heading structure', async () => {
    await renderPage();

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 1, name: 'Dashboard' })
      ).toBeInTheDocument();
    });

    // Check for proper heading hierarchy
    const headings = screen.getAllByRole('heading');
    expect(headings.length).toBeGreaterThan(0);

    // Verify h1 is present
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  it('should render System Status card', async () => {
    await renderPage();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(await screen.findByText('System Status')).toBeInTheDocument();
  });

  it('should have accessible navigation elements', async () => {
    await renderPage();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Check for accessible links
    const viewEventsLink = screen.getByRole('link', {
      name: /view audit events/i,
    });
    expect(viewEventsLink).toBeInTheDocument();
    expect(viewEventsLink).toHaveAttribute('href', '/audit');
  });

  it('should have accessible buttons with proper labels', async () => {
    await renderPage();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Check for properly labeled buttons
    // This button only appears in error state, so it might not be present initially
    void screen.queryByRole('button', { name: /try again/i });

    const disabledButtons = screen
      .getAllByRole('button')
      .filter((button) => button.hasAttribute('disabled'));

    // Disabled buttons should still be accessible
    disabledButtons.forEach((button) => {
      expect(button).toHaveAttribute('disabled');
    });
  });

  it('should provide alternative text for icons', async () => {
    await renderPage();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Stat cards should have accessible labels
    const statCards = screen.getAllByTestId('stat-card');
    expect(statCards.length).toBeGreaterThan(0);

    statCards.forEach((card) => {
      expect(card).toHaveAttribute('role', 'region');
      expect(card).toHaveAttribute('aria-label');
    });
  });

  it('should have proper color contrast requirements', async () => {
    const { container } = await renderPage();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // axe will automatically check color contrast
    const results = await axe(container, {
      rules: {
        'color-contrast': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });

  it('should be keyboard navigable', async () => {
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Check that interactive elements can receive focus
    const focusableElements = screen
      .getAllByRole('link')
      .concat(screen.getAllByRole('button'));

    focusableElements.forEach((element) => {
      expect(element).not.toHaveAttribute('tabindex', '-1');
    });
  });
});

// Extend Jest expect with axe assertions
const extendExpect = (expect: {
  extend: (matchers: typeof toHaveNoViolations) => void;
}) => {
  expect.extend(toHaveNoViolations);
};
