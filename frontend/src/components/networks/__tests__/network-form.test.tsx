import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import type React from 'react';
import { NetworkForm } from '../network-form';
import { WireGuardNetworkResponse } from '@/lib/api-client';

describe('NetworkForm', () => {
  const mockOnSubmit = jest.fn();
  let consoleErrorSpy: jest.SpyInstance;
  const renderForm = async (
    props: React.ComponentProps<typeof NetworkForm> = { onSubmit: mockOnSubmit }
  ) => {
    let view: ReturnType<typeof render> | undefined;
    await act(async () => {
      view = render(<NetworkForm {...props} />);
    });
    await act(async () => {});
    await waitFor(() => {
      expect(screen.getByLabelText('Name *')).toBeInTheDocument();
    });
    return view!;
  };

  beforeEach(() => {
    jest.clearAllMocks();
    const originalConsoleError = console.error;
    consoleErrorSpy = jest
      .spyOn(console, 'error')
      .mockImplementation((message, ...args) => {
        if (
          typeof message === 'string' &&
          message.includes('not wrapped in act')
        ) {
          return;
        }
        originalConsoleError(message, ...args);
      });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('should render form with all fields', async () => {
    await renderForm();

    await waitFor(() => {
      expect(screen.getByLabelText('Name *')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Name *')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Network CIDR *')).toBeInTheDocument();
    expect(screen.getByLabelText('DNS Servers')).toBeInTheDocument();
  });

  it('should populate form with initial data', async () => {
    const mockData: Partial<WireGuardNetworkResponse> = {
      name: 'Test Network',
      description: 'Test Description',
      network_cidr: '10.0.0.0/24',
      dns_servers: '1.1.1.1',
    };

    await renderForm({ data: mockData, onSubmit: mockOnSubmit });

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Network')).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('Test Network')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Description')).toBeInTheDocument();
    expect(screen.getByDisplayValue('10.0.0.0/24')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1.1.1.1')).toBeInTheDocument();
  });

  it('should show validation errors for required fields', async () => {
    await renderForm();

    const submitButton = screen.getByRole('button', { name: 'Save' });
    fireEvent.click(submitButton);

    // Since we're using react-hook-form with validation, the submit button should be disabled
    // and validation should prevent submission
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should submit form with valid data', async () => {
    await renderForm();

    const nameInput = screen.getByLabelText('Name *');
    const cidrInput = screen.getByLabelText('Network CIDR *');

    await act(async () => {
      fireEvent.change(nameInput, { target: { value: 'Test Network' } });
      fireEvent.change(cidrInput, { target: { value: '10.0.0.0/24' } });
    });

    // Submit the form directly and pass the event to prevent default behavior
    const form = nameInput.closest('form') as HTMLFormElement;
    if (form) {
      await act(async () => {
        const submitEvent = new Event('submit', {
          bubbles: true,
          cancelable: true,
        });
        Object.assign(submitEvent, { preventDefault: jest.fn() });
        form.dispatchEvent(submitEvent);
      });
    }

    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Test Network',
        network_cidr: '10.0.0.0/24',
      }),
      expect.any(Object)
    );
  });

  it('should disable fields when submitting', async () => {
    await renderForm({ onSubmit: mockOnSubmit, isSubmitting: true });

    await waitFor(() => {
      expect(screen.getByLabelText('Name *')).toBeDisabled();
    });

    expect(screen.getByLabelText('Name *')).toBeDisabled();
    expect(screen.getByLabelText('Description')).toBeDisabled();
    expect(screen.getByLabelText('Network CIDR *')).toBeDisabled();
    expect(screen.getByLabelText('DNS Servers')).toBeDisabled();
  });
});
