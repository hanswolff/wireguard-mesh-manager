import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FormProvider, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import {
  CidrInput,
  EndpointInput,
  IpAddressInput,
  IpAllowlistInput,
} from '../form-inputs';
import {
  cidrSchema,
  endpointSchema,
  ipAddressSchema,
  ipAllowlistSchema,
} from '@/lib/validation-schemas';

// Mock ipAllowlistSchema to validate based on input
const mockSafeParse = jest.spyOn(ipAllowlistSchema, 'safeParse');
mockSafeParse.mockImplementation((value: string) => {
  if (value === 'invalid-ip') {
    return { success: false, data: [], error: new Error('Invalid IP') };
  }
  return { success: true, data: [], error: undefined };
});

const TestForm: React.FC<{
  children: React.ReactNode;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  schema: z.ZodObject<any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  defaultValues?: any;
}> = ({ children, schema, defaultValues = {} }) => {
  const methods = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      cidr: '',
      endpoint: '',
      ipAddress: '',
      ipAllowlist: [],
      ...defaultValues,
    },
    mode: 'onChange',
  });

  return (
    <FormProvider {...methods}>
      <form>
        {children}
        <button type="submit" data-testid="submit">
          Submit
        </button>
      </form>
    </FormProvider>
  );
};

describe('Form Inputs', () => {
  const user = userEvent.setup();

  const testSchema = z.object({
    cidr: cidrSchema,
    endpoint: endpointSchema,
    ipAddress: ipAddressSchema,
    ipAllowlist: z.array(z.string()).default([]),
  });

  describe('CidrInput', () => {
    it('should render label and input', () => {
      render(
        <TestForm schema={testSchema}>
          <CidrInput name="cidr" label="Network CIDR" />
        </TestForm>
      );

      expect(screen.getByRole('textbox', { name: 'Network CIDR' })).toBeInTheDocument();
      expect(screen.getByPlaceholderText('192.168.1.0/24')).toBeInTheDocument();
    });

    it('should render description when provided', () => {
      render(
        <TestForm schema={testSchema}>
          <CidrInput name="cidr" description="Enter the network CIDR block" />
        </TestForm>
      );

      expect(
        screen.getByText('Enter the network CIDR block')
      ).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <TestForm schema={testSchema}>
          <CidrInput name="cidr" label="CIDR Input" className="custom-class" />
        </TestForm>
      );

      const container = screen
        .getByLabelText('CIDR Input')
        .closest('.custom-class');
      expect(container).toBeInTheDocument();
    });

    it('should show validation error for invalid CIDR', async () => {
      render(
        <TestForm schema={testSchema}>
          <CidrInput name="cidr" label="Network CIDR" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'Network CIDR' });
      await user.type(input, 'invalid-cidr');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.getByText('Invalid CIDR format (e.g., 192.168.1.0/24)')
        ).toBeInTheDocument();
      });
    });

    it('should accept valid CIDR', async () => {
      render(
        <TestForm schema={testSchema}>
          <CidrInput name="cidr" label="Network CIDR" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'Network CIDR' });
      await user.type(input, '192.168.1.0/24');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.queryByText('Invalid CIDR format (e.g., 192.168.1.0/24)')
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('EndpointInput', () => {
    it('should render label and input', () => {
      render(
        <TestForm schema={testSchema}>
          <EndpointInput name="endpoint" label="Endpoint" />
        </TestForm>
      );

      expect(screen.getByRole('textbox', { name: 'Endpoint' })).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText('example.com:51820')
      ).toBeInTheDocument();
    });

    it('should show validation error for invalid endpoint', async () => {
      render(
        <TestForm schema={testSchema}>
          <EndpointInput name="endpoint" label="Endpoint" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'Endpoint' });
      await user.type(input, 'invalid-endpoint');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.getByText(
            'Invalid endpoint format (e.g., example.com:51820 or 192.168.1.1:51820)'
          )
        ).toBeInTheDocument();
      });
    });

    it('should accept valid endpoint', async () => {
      render(
        <TestForm schema={testSchema}>
          <EndpointInput name="endpoint" label="Endpoint" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'Endpoint' });
      await user.type(input, 'example.com:51820');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.queryByText(
            'Invalid endpoint format (e.g., example.com:51820 or 192.168.1.1:51820)'
          )
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('IpAddressInput', () => {
    it('should render label and input', () => {
      render(
        <TestForm schema={testSchema}>
          <IpAddressInput name="ipAddress" label="IP Address" />
        </TestForm>
      );

      expect(screen.getByRole('textbox', { name: 'IP Address' })).toBeInTheDocument();
      expect(screen.getByPlaceholderText('192.168.1.1')).toBeInTheDocument();
    });

    it('should show validation error for invalid IP address', async () => {
      render(
        <TestForm schema={testSchema}>
          <IpAddressInput name="ipAddress" label="IP Address" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'IP Address' });
      await user.type(input, 'invalid-ip');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.getByText('Invalid IP address format (e.g., 192.168.1.1)')
        ).toBeInTheDocument();
      });
    });

    it('should accept valid IP address', async () => {
      render(
        <TestForm schema={testSchema}>
          <IpAddressInput name="ipAddress" label="IP Address" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'IP Address' });
      await user.type(input, '192.168.1.1');
      await user.tab();

      await waitFor(() => {
        expect(
          screen.queryByText('Invalid IP address format (e.g., 192.168.1.1)')
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('IpAllowlistInput', () => {
    it('should render input and add button', () => {
      render(
        <TestForm schema={testSchema} defaultValues={{ ipAllowlist: [] }}>
          <IpAllowlistInput name="ipAllowlist" label="IP Allowlist" />
        </TestForm>
      );

      expect(screen.getByRole('textbox', { name: 'IP Allowlist' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Add' })).toBeInTheDocument();
    });

    it('should add valid IP allowlist entry', async () => {
      render(
        <TestForm schema={testSchema} defaultValues={{ ipAllowlist: [] }}>
          <IpAllowlistInput name="ipAllowlist" label="IP Allowlist" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'IP Allowlist' });
      const addButton = screen.getByRole('button', { name: 'Add' });

      await user.clear(input);
      await user.type(input, '192.168.1.0/24');

      // Wait for button to be enabled
      await waitFor(() => {
        expect(addButton).not.toBeDisabled();
      });

      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('192.168.1.0/24')).toBeInTheDocument();
        expect(input).toHaveValue('');
      });
    });

    it('should remove IP allowlist entry', async () => {
      render(
        <TestForm
          schema={testSchema}
          defaultValues={{ ipAllowlist: ['192.168.1.0/24'] }}
        >
          <IpAllowlistInput name="ipAllowlist" label="IP Allowlist" />
        </TestForm>
      );

      const removeButton = screen.getByRole('button', { name: 'Remove' });

      expect(screen.getByText('192.168.1.0/24')).toBeInTheDocument();

      await user.click(removeButton);

      await waitFor(() => {
        expect(screen.queryByText('192.168.1.0/24')).not.toBeInTheDocument();
      });
    });

    it('should not add invalid IP allowlist entry', async () => {
      render(
        <TestForm schema={testSchema} defaultValues={{ ipAllowlist: [] }}>
          <IpAllowlistInput name="ipAllowlist" label="IP Allowlist" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'IP Allowlist' });
      const addButton = screen.getByRole('button', { name: 'Add' });

      await user.type(input, 'invalid-ip');

      await waitFor(() => {
        expect(addButton).toBeDisabled();
      });

      await user.click(addButton);

      await waitFor(() => {
        expect(screen.queryByText('invalid-ip')).not.toBeInTheDocument();
      });
    });

    it('should add entry on Enter key press', async () => {
      render(
        <TestForm schema={testSchema} defaultValues={{ ipAllowlist: [] }}>
          <IpAllowlistInput name="ipAllowlist" label="IP Allowlist" />
        </TestForm>
      );

      const input = screen.getByRole('textbox', { name: 'IP Allowlist' });

      await user.clear(input);
      await user.type(input, '192.168.1.1');

      // Wait for validation to pass before pressing Enter
      await waitFor(() => {
        expect(input).toHaveValue('192.168.1.1');
      });

      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
        expect(input).toHaveValue('');
      });
    });

    it('should disable add button when input is empty', () => {
      render(
        <TestForm schema={testSchema} defaultValues={{ ipAllowlist: [] }}>
          <IpAllowlistInput name="ipAllowlist" label="IP Allowlist" />
        </TestForm>
      );

      const addButton = screen.getByRole('button', { name: 'Add' });
      expect(addButton).toBeDisabled();
    });

    it('should render description when provided', () => {
      render(
        <TestForm schema={testSchema} defaultValues={{ ipAllowlist: [] }}>
          <IpAllowlistInput
            name="ipAllowlist"
            description="Enter IP addresses or CIDR blocks"
          />
        </TestForm>
      );

      expect(
        screen.getByText('Enter IP addresses or CIDR blocks')
      ).toBeInTheDocument();
    });

    it('should show multiple entries', () => {
      render(
        <TestForm
          schema={testSchema}
          defaultValues={{ ipAllowlist: ['192.168.1.0/24', '10.0.0.0/8'] }}
        >
          <IpAllowlistInput name="ipAllowlist" label="IP Allowlist" />
        </TestForm>
      );

      expect(screen.getByText('192.168.1.0/24')).toBeInTheDocument();
      expect(screen.getByText('10.0.0.0/8')).toBeInTheDocument();
    });
  });
});
