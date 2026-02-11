import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import AuditPage from '../page';
import { apiClient } from '@/lib/api';
import { UnlockProvider } from '@/contexts/unlock-context';

jest.mock('@radix-ui/react-presence', () => ({
  __esModule: true,
  Presence: ({
    children,
    present,
  }: {
    children: React.ReactNode;
    present: boolean;
  }) => (present ? <>{children}</> : null),
}));

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    getAuditEvents: jest.fn().mockResolvedValue({
      events: [
        {
          id: '1',
          created_at: '2024-01-15T10:30:00Z',
          actor: 'admin@example.com',
          action: 'CREATE',
          resource_type: 'NETWORK',
          resource_id: 'net-1234567890abcdef',
          network_id: 'net-1234567890abcdef',
          network_name: 'Test Network',
          device_id: null,
          details: {},
        },
        {
          id: '2',
          created_at: '2024-01-15T11:00:00Z',
          actor: 'system',
          action: 'UPDATE',
          resource_type: 'DEVICE',
          resource_id: 'device-abcdef1234567890',
          network_id: 'net-1234567890abcdef',
          network_name: 'Test Network',
          device_id: 'device-abcdef1234567890',
          details: {},
        },
      ],
      pagination: {
        total_count: 2,
        page: 1,
        page_size: 50,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
      filters_applied: {
        network_id: undefined,
        start_date: undefined,
        end_date: undefined,
        actor: undefined,
        action: undefined,
        resource_type: undefined,
      },
    }),
    exportAuditEvents: jest.fn().mockResolvedValue(new Blob()),
  },
}));

jest.mock('@/lib/api-client', () => {
  const apiClient = {
    isMasterPasswordUnlocked: jest.fn().mockResolvedValue({
      is_unlocked: false,
    }),
  };

  return {
    __esModule: true,
    default: apiClient,
    apiClient,
  };
});

// Mock the GlobalStateWrapper and EmptyState
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
    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;
    if (empty) return (
      <div data-testid="empty-state">
        <h3>No audit events</h3>
        <p>No audit events have been recorded yet.</p>
      </div>
    );
    return <div>{children}</div>;
  },
  EmptyState: ({
    title,
    description,
  }: {
    icon?: React.ComponentType<{ className?: string }>;
    title: string;
    description: string;
  }) => (
    <div data-testid="empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  ),
}));

// Mock the AuditFilters component
jest.mock('@/components/audit-filters', () => ({
  AuditFilters: ({
    filters,
    onChange,
    onClearFilters,
  }: {
    filters: { actor?: string; action?: string };
    onChange: (filters: Record<string, unknown>) => void;
    onClearFilters?: () => void;
  }) => (
    <div data-testid="audit-filters">
      <button
        type="button"
        onClick={() => onClearFilters && onClearFilters()}
        aria-label="Filter"
        data-testid="filter-button"
      >
        Filter
      </button>
      <input
        type="text"
        placeholder="Filter by actor"
        onChange={(e) => onChange({ ...filters, actor: e.target.value })}
        aria-label="Filter by actor"
      />
      <select
        onChange={(e) => onChange({ ...filters, action: e.target.value })}
        aria-label="Filter by action"
      >
        <option value="">All Actions</option>
        <option value="CREATE">Create</option>
        <option value="UPDATE">Update</option>
        <option value="DELETE">Delete</option>
      </select>
    </div>
  ),
}));

// Mock the constants
jest.mock('@/constants/audit', () => ({
  getActionColor: (action: string) => {
    const colors = {
      CREATE: 'bg-green-100 text-green-800',
      UPDATE: 'bg-blue-100 text-blue-800',
      DELETE: 'bg-red-100 text-red-800',
    };
    return colors[action as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  },
}));

describe('Audit Page Accessibility', () => {
  const user = userEvent.setup();
  const renderPage = async () => {
    const view = render(
      <UnlockProvider>
        <AuditPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(apiClient.getAuditEvents).toHaveBeenCalled();
    });

    return view;
  };

  beforeAll(() => {
    extendExpect(expect);
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should not have any accessibility violations', async () => {
    const { container } = await renderPage();

    // Wait for the component to fully load
    await waitFor(() => {
      expect(screen.getByText('Audit Events')).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper heading structure', async () => {
    await renderPage();

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 1, name: 'Audit Events' })
      ).toBeInTheDocument();
    });

    // Check for proper heading hierarchy
    const headings = screen.getAllByRole('heading');
    expect(headings.length).toBeGreaterThan(0);

    // Verify h1 is present (use more specific selector to avoid conflicts)
    expect(
      screen.getByRole('heading', { name: 'Audit Events' })
    ).toBeInTheDocument();
  });

  it('should have accessible data table', async () => {
    await renderPage();

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 1, name: 'Audit Events' })
      ).toBeInTheDocument();
    });

    const table = screen.queryByRole('table');
    if (table) {
      // Check for proper table structure
      expect(table).toBeInTheDocument();

      // Check for table headers
      const tableHeaders = screen.getAllByRole('columnheader');
      expect(tableHeaders.length).toBeGreaterThan(0);

      // Check that table headers have proper scope
      tableHeaders.forEach((header) => {
        expect(header).toHaveAttribute('scope');
      });
    } else {
      // Table might not be rendered if there are no events
      const emptyStateTitle = screen.getByText('No audit events found');
      expect(emptyStateTitle).toBeInTheDocument();
    }
  });

  it('should have accessible filter controls', async () => {
    await renderPage();

    await waitFor(() => {
      expect(screen.getByText('Audit Events')).toBeInTheDocument();
    });

    // Find the filter toggle button
    const filterButton = screen.getByRole('button', { name: /filter/i });
    expect(filterButton).toBeInTheDocument();

    // Toggle filters
    await user.click(filterButton);

    // Check for accessible filter inputs
    const actorFilter = screen.getByLabelText('Filter by actor');
    expect(actorFilter).toBeInTheDocument();

    const actionFilter = screen.getByLabelText('Filter by action');
    expect(actionFilter).toBeInTheDocument();
  });

  it('should have accessible action buttons', async () => {
    await renderPage();

    await waitFor(() => {
      // Wait for table to be available (indicates loading is complete)
      expect(screen.queryByRole('table')).toBeInTheDocument();
    });

    // Check for refresh button
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    expect(refreshButton).toBeInTheDocument();

    // Check for export buttons
    const exportButtons = screen.getAllByRole('button', { name: /export/i });
    expect(exportButtons.length).toBeGreaterThan(0);
  });

  it('should have proper keyboard navigation', async () => {
    await renderPage();

    await waitFor(() => {
      expect(screen.queryByRole('table')).toBeInTheDocument();
    });

    // Check that all interactive elements can receive focus
    const focusableElements = screen
      .getAllByRole('button')
      .concat(screen.queryAllByRole('combobox') || []);

    focusableElements.forEach((element) => {
      expect(element).not.toHaveAttribute('tabindex', '-1');
    });
  });

  it('should provide accessible data in table cells', async () => {
    await renderPage();

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument();
    });

    // Check that table data is properly associated with headers
    const tableRows = screen.getAllByRole('row');
    expect(tableRows.length).toBeGreaterThan(1); // Header + data rows

    // Check for badges with accessible text
    const badges = screen.getAllByText(/CREATE|UPDATE|DELETE/i); // Badges contain action text
    expect(badges.length).toBeGreaterThan(0);
    // TODO: Add aria-label to badges when component is updated
    // badges.forEach(badge => {
    //   expect(badge).toHaveAttribute('aria-label');
    // });
  });

  describe('Audit Page - Empty State', () => {
    beforeEach(() => {
      apiClient.getAuditEvents.mockResolvedValue({
        events: [],
        pagination: {
          total_count: 0,
          page: 1,
          page_size: 50,
          total_pages: 0,
          has_next: false,
          has_previous: false,
        },
        filters_applied: {
          network_id: undefined,
          start_date: undefined,
          end_date: undefined,
          actor: undefined,
          action: undefined,
          resource_type: undefined,
        },
      });
      apiClient.exportAuditEvents.mockResolvedValue('');
    });

    it('should handle empty state accessibly', async () => {
      await renderPage();

      await waitFor(() => {
        expect(screen.queryByTestId('empty-state')).toBeInTheDocument();
      });

      // Check that empty state has proper heading and description
      const emptyState = screen.queryByTestId('empty-state');
      expect(emptyState).toBeInTheDocument();
    });
  });

  describe('Audit Page - Data State', () => {
    beforeEach(() => {
      apiClient.getAuditEvents.mockResolvedValue({
        events: [
          {
            id: '1',
            created_at: '2024-01-15T10:30:00Z',
            actor: 'admin@example.com',
            action: 'CREATE',
            resource_type: 'NETWORK',
            resource_id: 'net-1234567890abcdef',
            network_id: 'net-1234567890abcdef',
            device_id: null,
            details: {},
          },
          {
            id: '2',
            created_at: '2024-01-15T11:00:00Z',
            actor: 'system',
            action: 'UPDATE',
            resource_type: 'DEVICE',
            resource_id: 'device-abcdef1234567890',
            network_id: 'net-1234567890abcdef',
            device_id: 'device-abcdef1234567890',
            details: {},
          },
        ],
        pagination: {
          total_count: 2,
          page: 1,
          page_size: 50,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
        filters_applied: {
          network_id: undefined,
          start_date: undefined,
          end_date: undefined,
          actor: undefined,
          action: undefined,
          resource_type: undefined,
        },
      });
      apiClient.exportAuditEvents.mockResolvedValue('');
    });

    it('should have proper ARIA labels and descriptions', async () => {
      await renderPage();

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });

      // Check for proper ARIA attributes
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      // Check that buttons have accessible labels
      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        const hasText = button.textContent?.trim().length > 0;
        const hasAriaLabel = button.hasAttribute('aria-label');
        const hasAriaLabelledBy = button.hasAttribute('aria-labelledby');

        expect(hasText || hasAriaLabel || hasAriaLabelledBy).toBe(true);
      });
    });

    it('should have accessible action buttons', async () => {
      await renderPage();

      await waitFor(() => {
        expect(screen.queryByRole('table')).toBeInTheDocument();
      });

      // Check for refresh button
      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      expect(refreshButton).toBeInTheDocument();

      // Check for export buttons
      const exportButtons = screen.getAllByRole('button', { name: /export/i });
      expect(exportButtons.length).toBeGreaterThan(0);
    });
  });
});

// Extend Jest expect with axe assertions
const extendExpect = (expect: {
  extend: (matchers: typeof toHaveNoViolations) => void;
}) => {
  expect.extend(toHaveNoViolations);
};
