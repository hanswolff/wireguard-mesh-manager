import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SecureTextarea } from '../secure-textarea';

describe('SecureTextarea', () => {
  const defaultProps = {
    placeholder: 'Enter text',
  };

  it('should render with default props', () => {
    render(<SecureTextarea {...defaultProps} />);

    const textarea = screen.getByPlaceholderText('Enter text');
    expect(textarea).toBeInTheDocument();
  });

  it('should use secure placeholder for secure fields', () => {
    render(
      <SecureTextarea
        name="secret-key"
        placeholder="Normal placeholder"
        securePlaceholder="Secure placeholder"
      />
    );

    const textarea = screen.getByPlaceholderText('Secure placeholder');
    expect(textarea).toBeInTheDocument();
  });

  it('should identify secure fields by name', () => {
    const secureNames = ['password', 'secret', 'api-key'];

    secureNames.forEach((name) => {
      const { unmount } = render(
        <SecureTextarea
          name={name}
          placeholder="Normal placeholder"
          securePlaceholder="Secure placeholder"
        />
      );

      expect(
        screen.getByPlaceholderText('Secure placeholder')
      ).toBeInTheDocument();
      unmount();
    });
  });

  it('should not identify non-secure fields', () => {
    const nonSecureNames = ['description', 'content', 'message', 'notes'];

    nonSecureNames.forEach((name) => {
      const { unmount } = render(
        <SecureTextarea
          name={name}
          placeholder="Normal placeholder"
          securePlaceholder="Secure placeholder"
        />
      );

      expect(
        screen.getByPlaceholderText('Normal placeholder')
      ).toBeInTheDocument();
      unmount();
    });
  });

  it('should be case insensitive when detecting secure fields', () => {
    const secureVariants = [
      'SECRET',
      'Secret',
      'SeCrEt',
      'PASSWORD',
      'Api-Key',
    ];

    secureVariants.forEach((name) => {
      const { unmount } = render(
        <SecureTextarea
          name={name}
          placeholder="Normal placeholder"
          securePlaceholder="Secure placeholder"
        />
      );

      expect(
        screen.getByPlaceholderText('Secure placeholder')
      ).toBeInTheDocument();
      unmount();
    });
  });

  it('should generate random attributes to prevent autofill', () => {
    render(<SecureTextarea {...defaultProps} />);

    const textarea = screen.getByPlaceholderText('Enter text');

    expect(textarea).toHaveAttribute('autocomplete', 'new-password');
    expect(textarea).toHaveAttribute('autocorrect', 'off');
    expect(textarea).toHaveAttribute('autocapitalize', 'off');
    expect(textarea).toHaveAttribute('spellcheck', 'false');
    expect(textarea).toHaveAttribute('data-lpignore', 'true');
    expect(textarea).toHaveAttribute('data-bv-msgfield');
  });

  it('should use custom id and name when provided', () => {
    render(
      <SecureTextarea {...defaultProps} id="custom-id" name="custom-name" />
    );

    const textarea = screen.getByPlaceholderText('Enter text');
    expect(textarea).toHaveAttribute('id', 'custom-id');
    expect(textarea).toHaveAttribute('name', 'custom-name');
  });

  it('should apply custom className', () => {
    render(<SecureTextarea {...defaultProps} className="custom-class" />);

    const textarea = screen.getByPlaceholderText('Enter text');
    expect(textarea).toHaveClass('custom-class');
  });

  it('should handle input value changes', async () => {
    const user = userEvent.setup();
    render(<SecureTextarea {...defaultProps} />);

    const textarea = screen.getByPlaceholderText('Enter text');
    await user.type(textarea, 'test content');

    expect(textarea).toHaveValue('test content');
  });

  it('should call onChange handler when value changes', async () => {
    const user = userEvent.setup();
    const mockOnChange = jest.fn();
    render(<SecureTextarea {...defaultProps} onChange={mockOnChange} />);

    const textarea = screen.getByPlaceholderText('Enter text');
    await user.type(textarea, 'test');

    expect(mockOnChange).toHaveBeenCalledTimes(4); // Called for each character
  });

  it('should not use secure placeholder when not provided', () => {
    render(
      <SecureTextarea name="secret-key" placeholder="Normal placeholder" />
    );

    const textarea = screen.getByPlaceholderText('Normal placeholder');
    expect(textarea).toBeInTheDocument();
  });

  it('should handle default textarea props', () => {
    render(<SecureTextarea {...defaultProps} rows={5} cols={30} disabled />);

    const textarea = screen.getByPlaceholderText('Enter text');
    expect(textarea).toHaveAttribute('rows', '5');
    expect(textarea).toHaveAttribute('cols', '30');
    expect(textarea).toBeDisabled();
  });

  it('should apply proper styling classes', () => {
    render(<SecureTextarea {...defaultProps} />);

    const textarea = screen.getByPlaceholderText('Enter text');
    const baseClasses = [
      'file:text-foreground',
      'placeholder:text-muted-foreground',
      'selection:bg-primary',
      'selection:text-primary-foreground',
      'dark:bg-input/30',
      'border-input',
      'flex',
      'min-h-[60px]',
      'w-full',
      'rounded-md',
      'border',
      'bg-transparent',
      'px-3',
      'py-2',
      'text-base',
      'shadow-xs',
      'transition-[color,box-shadow]',
      'outline-none',
      'file:inline-flex',
      'file:h-7',
      'file:border-0',
      'file:bg-transparent',
      'file:text-sm',
      'file:font-medium',
      'disabled:pointer-events-none',
      'disabled:cursor-not-allowed',
      'disabled:opacity-50',
      'md:text-sm',
      'focus-visible:border-ring',
      'focus-visible:ring-ring/50',
      'focus-visible:ring-[3px]',
      'aria-invalid:ring-destructive/20',
      'dark:aria-invalid:ring-destructive/40',
      'aria-invalid:border-destructive',
    ];

    baseClasses.forEach((className) => {
      expect(textarea).toHaveClass(className);
    });
  });

  it('should handle focus and blur events', async () => {
    const user = userEvent.setup();
    const mockOnFocus = jest.fn();
    const mockOnBlur = jest.fn();

    render(
      <SecureTextarea
        {...defaultProps}
        onFocus={mockOnFocus}
        onBlur={mockOnBlur}
      />
    );

    const textarea = screen.getByPlaceholderText('Enter text');

    await user.click(textarea);
    expect(mockOnFocus).toHaveBeenCalledTimes(1);

    await user.tab(); // Move focus away
    expect(mockOnBlur).toHaveBeenCalledTimes(1);
  });
});
