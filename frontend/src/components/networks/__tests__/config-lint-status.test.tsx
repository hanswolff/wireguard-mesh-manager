import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigLintStatus } from '../config-lint-status';
import { type ConfigLintResponse } from '@/lib/api-client';

const mockLintResults: ConfigLintResponse = {
  valid: false,
  summary: 'Found 2 issues in configuration',
  issues: [
    {
      severity: 'error',
      category: 'network',
      field: 'network_cidr',
      message: 'Invalid CIDR notation',
      suggestion: 'Use proper CIDR format (e.g., 192.168.1.0/24)',
    },
    {
      severity: 'warning',
      category: 'network',
      field: 'dns_servers',
      message: 'Common DNS servers detected',
      suggestion: 'Consider using custom DNS servers for better privacy',
    },
  ],
  issue_count: {
    error: 1,
    warning: 1,
    info: 0,
  },
};

describe('ConfigLintStatus', () => {
  it('should show loading state when lintLoading is true', () => {
    render(
      <ConfigLintStatus
        lintResults={null}
        lintLoading={true}
        onRefresh={jest.fn()}
      />
    );

    expect(screen.getByText('Validating configuration...')).toBeInTheDocument();
  });

  it('should show empty state when no results and not loading', () => {
    render(
      <ConfigLintStatus
        lintResults={null}
        lintLoading={false}
        onRefresh={jest.fn()}
      />
    );

    expect(
      screen.getByText('Configuration validation not yet performed')
    ).toBeInTheDocument();
  });

  it('should display validation results when available', () => {
    render(
      <ConfigLintStatus
        lintResults={mockLintResults}
        lintLoading={false}
        onRefresh={jest.fn()}
      />
    );

    expect(screen.getByText('Configuration has issues')).toBeInTheDocument();
    expect(
      screen.getByText('Found 2 issues in configuration')
    ).toBeInTheDocument();
    expect(screen.getByText('1 Error')).toBeInTheDocument();
    expect(screen.getByText('1 Warning')).toBeInTheDocument();
  });

  it('should show valid status when configuration is valid', () => {
    const validResults: ConfigLintResponse = {
      valid: true,
      summary: 'Configuration is valid',
      issues: [],
      issue_count: {},
    };

    render(
      <ConfigLintStatus
        lintResults={validResults}
        lintLoading={false}
        onRefresh={jest.fn()}
      />
    );

    expect(
      screen.getByText('Configuration is valid', { selector: '.font-medium' })
    ).toBeInTheDocument();
  });

  it('should display individual issues correctly', () => {
    render(
      <ConfigLintStatus
        lintResults={mockLintResults}
        lintLoading={false}
        onRefresh={jest.fn()}
      />
    );

    expect(screen.getByText('Issues Found:')).toBeInTheDocument();
    expect(screen.getAllByText('network')).toHaveLength(2);
    expect(screen.getByText('network_cidr')).toBeInTheDocument();
    expect(screen.getByText('Invalid CIDR notation')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Suggestion: Use proper CIDR format (e.g., 192.168.1.0/24)'
      )
    ).toBeInTheDocument();
  });

  it('should call onRefresh when refresh button is clicked', async () => {
    const mockOnRefresh = jest.fn();
    const user = userEvent.setup();

    render(
      <ConfigLintStatus
        lintResults={mockLintResults}
        lintLoading={false}
        onRefresh={mockOnRefresh}
      />
    );

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);

    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('should disable refresh button when loading', () => {
    render(
      <ConfigLintStatus
        lintResults={null}
        lintLoading={true}
        onRefresh={jest.fn()}
      />
    );

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    expect(refreshButton).toBeDisabled();
  });
});
