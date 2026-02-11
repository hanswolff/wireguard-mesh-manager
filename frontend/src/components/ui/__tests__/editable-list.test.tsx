import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Globe } from 'lucide-react';
import { EditableList } from '../editable-list';

describe('EditableList', () => {
  const mockOnChange = jest.fn();

  const defaultProps = {
    items: [],
    onChange: mockOnChange,
    placeholder: 'https://example.com',
    label: 'Allowed Origins',
    Icon: Globe,
  };

  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    jest.clearAllMocks();
    user = userEvent.setup();
  });

  describe('Rendering', () => {
    it('should render input and add button', () => {
      render(<EditableList {...defaultProps} />);

      expect(
        screen.getByPlaceholderText('https://example.com')
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /add/i })
      ).toBeInTheDocument();
    });

    it('should render empty state when no items', () => {
      render(<EditableList {...defaultProps} />);

      expect(screen.getByText('No items configured')).toBeInTheDocument();
      expect(
        screen.getByText('Add an item to get started')
      ).toBeInTheDocument();
    });

    it('should render items when provided', () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      expect(screen.getByText('Allowed Origins')).toBeInTheDocument();
      expect(screen.getByText('https://example.com')).toBeInTheDocument();
      expect(
        screen.queryByText('No items configured')
      ).not.toBeInTheDocument();
    });

    it('should render custom empty state messages', () => {
      render(
        <EditableList
          {...defaultProps}
          emptyStateTitle="No CORS origins configured"
          emptyStateDescription="Add an origin to enable cross-origin requests"
        />
      );

      expect(screen.getByText('No CORS origins configured')).toBeInTheDocument();
      expect(
        screen.getByText('Add an origin to enable cross-origin requests')
      ).toBeInTheDocument();
    });

    it('should render description when provided', () => {
      render(
        <EditableList
          {...defaultProps}
          description="This is a description"
        />
      );

      expect(screen.getByText('This is a description')).toBeInTheDocument();
    });

    it('should render icon when provided', () => {
      render(<EditableList {...defaultProps} Icon={Globe} />);

      const icon = document.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should render without icon when not provided', () => {
      render(<EditableList {...defaultProps} Icon={undefined} />);

      expect(screen.getByPlaceholderText('https://example.com')).toBeInTheDocument();
    });
  });

  describe('Adding Items', () => {
    it('should add item when add button is clicked', async () => {
      render(<EditableList {...defaultProps} items={[]} />);

      const input = screen.getByPlaceholderText('https://example.com');
      const addButton = screen.getByRole('button', { name: /Add Allowed Origins/i });

      await user.type(input, 'https://example.com');
      await user.click(addButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(['https://example.com']);
      });
      expect(input).toHaveValue('');
    });

    it('should add item on Enter key press', async () => {
      render(<EditableList {...defaultProps} items={[]} />);

      const input = screen.getByPlaceholderText('https://example.com');

      await user.type(input, 'https://example.com');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(['https://example.com']);
      });
      expect(input).toHaveValue('');
    });

    it('should disable add button when input is empty', () => {
      render(<EditableList {...defaultProps} items={[]} />);

      const addButton = screen.getByRole('button', { name: /add/i });
      expect(addButton).toBeDisabled();
    });

    it('should disable add button when item already exists', async () => {
      render(
        <EditableList
          {...defaultProps}
          items={['https://example.com']}
        />
      );

      const input = screen.getByPlaceholderText('https://example.com');
      const addButton = screen.getByRole('button', { name: /add/i });

      await user.type(input, 'https://example.com');

      expect(addButton).toBeDisabled();
    });

    it('should trim whitespace from new items', async () => {
      render(<EditableList {...defaultProps} items={[]} />);

      const input = screen.getByPlaceholderText('https://example.com');
      const addButton = screen.getByRole('button', { name: /add/i });

      await user.type(input, '  https://example.com  ');
      await user.click(addButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(['https://example.com']);
      });
    });
  });

  describe('Removing Items', () => {
    it('should remove item when remove button is clicked', async () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const removeButton = screen.getByRole('button', { name: /remove/i });

      expect(screen.getByText('https://example.com')).toBeInTheDocument();

      await user.click(removeButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith([]);
      });
      expect(
        screen.queryByText('https://example.com')
      ).not.toBeInTheDocument();
    });

    it('should show remove button on hover', () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const removeButton = screen.getByRole('button', { name: /remove/i });
      expect(removeButton).toHaveClass('opacity-0');
    });
  });

  describe('Editing Items', () => {
    it('should enter edit mode when edit button is clicked', async () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });

      await user.click(editButton);

      await waitFor(() => {
        expect(screen.getByDisplayValue('https://example.com')).toBeInTheDocument();
      });
    });

    it('should save edited item when check button is clicked', async () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      const input = screen.getByDisplayValue('https://example.com');
      await user.clear(input);
      await user.type(input, 'https://newexample.com');

      const saveButton = screen.getByRole('button', { name: /check/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(['https://newexample.com']);
      });
    });

    it('should save edited item on Enter key press', async () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      const input = screen.getByDisplayValue('https://example.com');
      await user.clear(input);
      await user.type(input, 'https://newexample.com');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(['https://newexample.com']);
      });
    });

    it('should cancel edit when X button is clicked', async () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      const input = screen.getByDisplayValue('https://example.com');
      await user.clear(input);
      await user.type(input, 'https://newexample.com');

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      await waitFor(() => {
        expect(mockOnChange).not.toHaveBeenCalled();
        expect(screen.getByText('https://example.com')).toBeInTheDocument();
      });
    });

    it('should cancel edit on Escape key press', async () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      const input = screen.getByDisplayValue('https://example.com');
      await user.clear(input);
      await user.type(input, 'https://newexample.com');
      await user.keyboard('{Escape}');

      await waitFor(() => {
        expect(mockOnChange).not.toHaveBeenCalled();
        expect(screen.getByText('https://example.com')).toBeInTheDocument();
      });
    });

    it('should trim whitespace from edited items', async () => {
      render(
        <EditableList {...defaultProps} items={['https://example.com']} />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      const input = screen.getByDisplayValue('https://example.com');
      await user.clear(input);
      await user.type(input, '  https://newexample.com  ');

      const saveButton = screen.getByRole('button', { name: /check/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(['https://newexample.com']);
      });
    });
  });

  describe('Multiple Items', () => {
    it('should render multiple items', () => {
      render(
        <EditableList
          {...defaultProps}
          items={[
            'https://example.com',
            'https://another.com',
            'https://third.com',
          ]}
        />
      );

      expect(screen.getByText('https://example.com')).toBeInTheDocument();
      expect(screen.getByText('https://another.com')).toBeInTheDocument();
      expect(screen.getByText('https://third.com')).toBeInTheDocument();
    });

    it('should remove correct item when multiple items exist', async () => {
      render(
        <EditableList
          {...defaultProps}
          items={['https://example.com', 'https://another.com']}
        />
      );

      const removeButtons = screen.getAllByRole('button', { name: /remove/i });

      await user.click(removeButtons[0]);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(['https://another.com']);
      });
    });
  });

  describe('Disabled State', () => {
    it('should disable input when disabled', () => {
      render(<EditableList {...defaultProps} disabled />);

      const input = screen.getByPlaceholderText('https://example.com');
      expect(input).toBeDisabled();
    });

    it('should disable add button when disabled', () => {
      render(<EditableList {...defaultProps} disabled />);

      const addButton = screen.getByRole('button', { name: /add/i });
      expect(addButton).toBeDisabled();
    });

    it('should disable edit and remove buttons when disabled', () => {
      render(
        <EditableList
          {...defaultProps}
          items={['https://example.com']}
          disabled
        />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });
      const removeButton = screen.getByRole('button', { name: /remove/i });

      expect(editButton).toBeDisabled();
      expect(removeButton).toBeDisabled();
    });
  });
});
