import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import NetworksPage from '../page';
import { UnlockProvider } from '@/contexts/unlock-context';

// Mock the API client
jest.mock('@/lib/api-client', () => {
  const apiClient = {
    isMasterPasswordUnlocked: jest.fn().mockResolvedValue({
      is_unlocked: false,
    }),
    getMasterPasswordStatus: jest.fn().mockResolvedValue({
      is_unlocked: false,
      password_id: null,
      expires_at: null,
      idle_expires_at: null,
      access_count: 0,
      last_access: null,
      ttl_seconds: 0,
      idle_ttl_seconds: 0,
    }),
    listNetworks: jest.fn().mockResolvedValue([
      {
        id: 'net-1',
        name: 'Main Office Network',
        description: 'Primary network for office connectivity',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-15T10:30:00Z',
        device_count: 5,
        location_count: 2,
        network_cidr: '10.0.0.0/24',
      },
      {
        id: 'net-2',
        name: 'Remote Workers',
        description: 'Network for remote employee access',
        created_at: '2024-01-05T00:00:00Z',
        updated_at: '2024-01-10T15:45:00Z',
        device_count: 12,
        location_count: 1,
        network_cidr: '10.1.0.0/24',
      },
    ]),
    createNetwork: jest.fn().mockResolvedValue({
      id: 'net-3',
      name: 'Test Network',
      description: 'Test description',
      created_at: '2024-01-15T00:00:00Z',
      updated_at: '2024-01-15T00:00:00Z',
      device_count: 0,
      location_count: 0,
      network_cidr: '10.2.0.0/24',
    }),
    updateNetwork: jest.fn().mockResolvedValue({
      id: 'net-1',
      name: 'Updated Network',
      description: 'Updated description',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-15T00:00:00Z',
      device_count: 5,
      location_count: 2,
      network_cidr: '10.0.0.0/24',
    }),
    deleteNetwork: jest.fn().mockResolvedValue(undefined),
  };

  return {
    __esModule: true,
    default: apiClient,
    apiClient,
  };
});

// Mock the toast component
jest.mock('@/components/ui/use-toast', () => ({
  toast: jest.fn(),
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    refresh: jest.fn(),
  }),
}));

describe('Networks Page Accessibility', () => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const user = userEvent.setup();

  beforeAll(() => {
    extendExpect(expect);
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should not have any accessibility violations', async () => {
    const { container } = render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    // Wait for the component to fully load
    await waitFor(() => {
      expect(screen.getByText('Networks')).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper heading structure', async () => {
    render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 1, name: 'Networks' })
      ).toBeInTheDocument();
    });

    // Check for proper heading hierarchy
    const headings = screen.getAllByRole('heading');
    expect(headings.length).toBeGreaterThan(0);

    // Verify h1 is present
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  it('should have accessible navigation elements', async () => {
    render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Networks')).toBeInTheDocument();
    });

    // Check for create network buttons (there are two - header and empty state)
    const createButtons = screen.getAllByRole('button', {
      name: /create network/i,
    });
    expect(createButtons.length).toBeGreaterThan(0);

    // Check for export link/button if present
    const exportLink = screen.queryByRole('link', { name: /export/i });
    if (exportLink) {
      expect(exportLink).toBeInTheDocument();
    }
  });

  it('should have accessible network table', async () => {
    render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Networks')).toBeInTheDocument();
    });

    const table = screen.queryByRole('table');

    if (table) {
      // Check for proper table structure when data is present
      expect(table).toBeInTheDocument();

      // Check for table headers
      const tableHeaders = screen.getAllByRole('columnheader');
      expect(tableHeaders.length).toBeGreaterThan(0);

      // Check that table headers have proper scope
      tableHeaders.forEach((header) => {
        expect(header).toHaveAttribute('scope', 'col');
      });

      // Check for table rows
      const tableRows = screen.getAllByRole('row');
      expect(tableRows.length).toBeGreaterThan(1); // Header + data rows
    } else {
      // If no table, should be in empty state
      const emptyState = screen.getByText(/no networks found/i);
      expect(emptyState).toBeInTheDocument();
    }
  });

  it('should have proper keyboard navigation', async () => {
    render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Networks')).toBeInTheDocument();
    });

    // Check that all interactive elements can receive focus
    const buttons = screen.getAllByRole('button');
    const links = screen.queryAllByRole('link');
    const focusableElements = buttons.concat(links);

    focusableElements.forEach((element) => {
      expect(element).not.toHaveAttribute('tabindex', '-1');
    });

    // Ensure there are some focusable elements
    expect(focusableElements.length).toBeGreaterThan(0);
  });

  it('should provide accessible search and filtering', async () => {
    render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Networks')).toBeInTheDocument();
    });

    // Look for search input by placeholder text
    const searchInput = screen.getByPlaceholderText(/search networks/i);
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveAttribute('aria-label', 'Search networks');

    // Look for sort controls if table is present
    const table = screen.queryByRole('table');
    if (table) {
      const sortableHeaders = screen
        .getAllByRole('columnheader')
        .filter(
          (header) =>
            header.hasAttribute('aria-sort') ||
            header.classList.contains('cursor-pointer')
        );
      expect(sortableHeaders.length).toBeGreaterThan(0);
    }
  });

  it('should handle empty state accessibly', async () => {
    // Mock empty response
    const mockListNetworks = jest.fn().mockResolvedValue([]);

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { apiClient } = require('@/lib/api-client');
    apiClient.listNetworks = mockListNetworks;

    render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('No networks found')).toBeInTheDocument();
    });

    // Check that empty state has proper message
    const emptyMessage = screen.getByText(/no networks found/i);
    expect(emptyMessage).toBeInTheDocument();
  });

  it('should have proper ARIA labels and descriptions', async () => {
    render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Networks')).toBeInTheDocument();
    });

    // Check that buttons have accessible labels
    const buttons = screen.getAllByRole('button');
    buttons.forEach((button) => {
      const hasText = button.textContent?.trim().length > 0;
      const hasAriaLabel = button.hasAttribute('aria-label');
      const hasAriaLabelledBy = button.hasAttribute('aria-labelledby');

      expect(hasText || hasAriaLabel || hasAriaLabelledBy).toBe(true);
    });

    // Check table if present
    const table = screen.queryByRole('table');
    if (table) {
      expect(table).toBeInTheDocument();

      // Check for table caption
      const caption = table.querySelector('caption');
      if (caption) {
        expect(caption).toBeInTheDocument();
      }

      // Check for accessible actions dropdown menus
      const dropdownTriggers = screen
        .getAllByRole('button')
        .filter((button) => button.hasAttribute('aria-haspopup'));
      expect(dropdownTriggers.length).toBeGreaterThan(0);
    }
  });

  it('should maintain color contrast requirements', async () => {
    const { container } = render(
      <UnlockProvider>
        <NetworksPage />
      </UnlockProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Networks')).toBeInTheDocument();
    });

    // axe will automatically check color contrast
    const results = await axe(container, {
      rules: {
        'color-contrast': { enabled: true },
      },
    });
    expect(results).toHaveNoViolations();
  });
});

// Extend Jest expect with axe assertions
const extendExpect = (expect: {
  extend: (matchers: typeof toHaveNoViolations) => void;
}) => {
  expect.extend(toHaveNoViolations);
};
