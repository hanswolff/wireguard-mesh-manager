'use client';

import * as React from 'react';
import { AlertTriangle, Trash2, AlertCircle, Info } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

export type ConfirmDialogVariant = 'destructive' | 'warning' | 'info';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmDialogVariant;
  isConfirming?: boolean;
  requiresCheckbox?: boolean;
  checkboxLabel?: string;
  validationText?: string;
  showSecurityNotice?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'destructive',
  isConfirming = false,
  requiresCheckbox = false,
  checkboxLabel = 'I understand this action cannot be undone',
  validationText,
  showSecurityNotice = false,
}: ConfirmDialogProps) {
  const [isChecked, setIsChecked] = React.useState(false);
  const [validationInput, setValidationInput] = React.useState('');

  const canConfirm = requiresCheckbox
    ? isChecked
    : validationText
      ? validationInput === validationText
      : true;

  const handleConfirm = () => {
    if (canConfirm) {
      onConfirm();
      // Reset state
      setIsChecked(false);
      setValidationInput('');
    }
  };

  const handleClose = () => {
    onClose();
    // Reset state
    setIsChecked(false);
    setValidationInput('');
  };

  const iconConfig = {
    destructive: {
      icon: <Trash2 className="h-5 w-5 text-destructive" />,
      variant: 'destructive' as const,
    },
    warning: {
      icon: <AlertTriangle className="h-5 w-5 text-warning" />,
      variant: 'destructive' as const,
    },
    info: {
      icon: <Info className="h-5 w-5 text-info" />,
      variant: 'default' as const,
    },
  };

  const getIcon = () => iconConfig[variant].icon;
  const getConfirmButtonVariant = () => iconConfig[variant].variant;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getIcon()}
            {title}
          </DialogTitle>
          <DialogDescription className="text-sm">
            {description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Checkbox Confirmation */}
          {requiresCheckbox && (
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="confirm-checkbox"
                checked={isChecked}
                onChange={(e) => setIsChecked(e.target.checked)}
                className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
              />
              <label
                htmlFor="confirm-checkbox"
                className="text-sm text-muted-foreground cursor-pointer"
              >
                {checkboxLabel}
              </label>
            </div>
          )}

          {/* Text Validation */}
          {validationText && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Type{' '}
                <code className="bg-muted px-1 py-0.5 rounded text-xs">
                  {validationText}
                </code>{' '}
                to confirm:
              </p>
              <input
                type="text"
                value={validationInput}
                onChange={(e) => setValidationInput(e.target.value)}
                placeholder={validationText}
                className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
          )}

          {/* Security Notice */}
          {showSecurityNotice && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                This action will be logged for audit purposes and cannot be
                undone.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isConfirming}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={getConfirmButtonVariant()}
            onClick={handleConfirm}
            disabled={!canConfirm || isConfirming}
          >
            {isConfirming ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                Processing...
              </>
            ) : (
              confirmText
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
