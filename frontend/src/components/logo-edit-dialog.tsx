'use client';

import { useState, useEffect } from 'react';
import { apiClient, OperationalSettingsResponse } from '@/lib/api-client';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { LoadingButton } from '@/components/ui/loading-button';
import { Palette, Type, Layout, Save, X, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { getContrastColor } from '@/lib/utils/color-utils';

interface LogoEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  settings: OperationalSettingsResponse;
  onSave?: () => void;
}

type FieldError = {
  logo_bg_color?: string;
  logo_text?: string;
  app_name?: string;
};

export function LogoEditDialog({
  open,
  onOpenChange,
  settings: initialSettings,
  onSave,
}: LogoEditDialogProps) {
  const [logoBgColor, setLogoBgColor] = useState(initialSettings.logo_bg_color);
  const [logoText, setLogoText] = useState(initialSettings.logo_text);
  const [appName, setAppName] = useState(initialSettings.app_name);
  const [isSaving, setIsSaving] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldError>({});
  const [touched, setTouched] = useState({ logo_bg_color: false, logo_text: false, app_name: false });

  const hasChanges =
    logoBgColor !== initialSettings.logo_bg_color ||
    logoText !== initialSettings.logo_text ||
    appName !== initialSettings.app_name;

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (!open) {
      setLogoBgColor(initialSettings.logo_bg_color);
      setLogoText(initialSettings.logo_text);
      setAppName(initialSettings.app_name);
      setGeneralError(null);
      setFieldErrors({});
      setTouched({ logo_bg_color: false, logo_text: false, app_name: false });
    }
  }, [open, initialSettings.logo_bg_color, initialSettings.logo_text, initialSettings.app_name]);

  const validateHexColor = (value: string): string | null => {
    if (!value) return null;
    const hexPattern = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/;
    if (!hexPattern.test(value)) {
      return 'Must be a valid hex color (e.g., #FF5733, #F53)';
    }
    return null;
  };

  const validateLogoText = (value: string): string | null => {
    if (value === undefined || value === null) return null;
    if (value.length === 0) {
      return 'Logo text is required';
    }
    if (value.length > 3) {
      return 'Must be 1-3 characters long';
    }
    if (!/^[A-Za-z0-9]+$/.test(value)) {
      return 'Must contain only alphanumeric characters';
    }
    return null;
  };

  const validateAppName = (value: string): string | null => {
    if (value === undefined || value === null) return null;
    if (value.length === 0) {
      return 'App name is required';
    }
    if (value.length > 100) {
      return 'Must not exceed 100 characters';
    }
    return null;
  };

  const isValidHexColor = !validateHexColor(logoBgColor);
  const isValidLogoText = !validateLogoText(logoText);
  const isValidAppName = !validateAppName(appName);
  const logoBgColorError = touched.logo_bg_color ? (fieldErrors.logo_bg_color || validateHexColor(logoBgColor)) : null;
  const logoTextError = touched.logo_text ? (fieldErrors.logo_text || validateLogoText(logoText)) : null;
  const appNameError = touched.app_name ? (fieldErrors.app_name || validateAppName(appName)) : null;

  const handleBlur = (field: 'logo_bg_color' | 'logo_text' | 'app_name') => {
    setTouched(prev => ({ ...prev, [field]: true }));
  };

  const handleSave = async () => {
    // Validate all fields before saving
    const logoBgColorValidationError = validateHexColor(logoBgColor);
    const logoTextValidationError = validateLogoText(logoText);
    const appNameValidationError = validateAppName(appName);

    if (logoBgColorValidationError || logoTextValidationError || appNameValidationError) {
      setTouched({ logo_bg_color: true, logo_text: true, app_name: true });
      setFieldErrors({});
      return;
    }

    setIsSaving(true);
    setGeneralError(null);
    setFieldErrors({});

    try {
      const updatePayload: any = {};

      if (logoBgColor !== initialSettings.logo_bg_color) {
        updatePayload.logo_bg_color = logoBgColor;
      }
      if (logoText !== initialSettings.logo_text) {
        updatePayload.logo_text = logoText;
      }
      if (appName !== initialSettings.app_name) {
        updatePayload.app_name = appName;
      }

      if (Object.keys(updatePayload).length === 0) {
        onOpenChange(false);
        setIsSaving(false);
        return;
      }

      const updated = await apiClient.updateOperationalSettings(updatePayload);
      setGeneralError(null);
      setFieldErrors({});
      onSave?.();
      onOpenChange(false);
    } catch (err: any) {
      if (err.fieldErrors) {
        // Set field-specific errors from backend
        setFieldErrors(err.fieldErrors);
      } else if (err.status === 422) {
        // Validation error from backend
        setGeneralError(err.message || 'Validation failed');
      } else if (err.status === 500) {
        // Internal server error
        setGeneralError(err.message || 'An unexpected server error occurred. Please try again later.');
      } else if (err.isUnauthorized) {
        setGeneralError('Master password is locked. Please unlock to save changes.');
      } else {
        // Generic error (network errors, timeouts, etc.)
        setGeneralError(err.message || 'Failed to save logo settings. Please try again.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Logo</DialogTitle>
          <DialogDescription>
            Customize logo appearance in sidebar. Changes are saved to operational settings.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {generalError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{generalError}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="logoText" className={logoTextError ? "text-destructive" : ""}>
                <Type className="inline-block w-4 h-4 mr-2" />
                Logo Text (1-3 characters)
              </Label>
              <Input
                id="logoText"
                value={logoText}
                onChange={(e) => {
                  const value = e.target.value.toUpperCase();
                  setLogoText(value);
                }}
                onBlur={() => handleBlur('logo_text')}
                placeholder="WG"
                maxLength={3}
                disabled={isSaving}
                className={logoTextError ? "border-destructive" : ""}
              />
              {logoTextError && (
                <p className="text-sm text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {logoTextError}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="logoBgColor" className={logoBgColorError ? "text-destructive" : ""}>
                <Palette className="inline-block w-4 h-4 mr-2" />
                Background Color (hex)
              </Label>
              <div className="flex gap-2">
                <div className="flex-1">
                  <Input
                    id="logoBgColor"
                    value={logoBgColor}
                    onChange={(e) => setLogoBgColor(e.target.value)}
                    onBlur={() => handleBlur('logo_bg_color')}
                    placeholder="#000000"
                    disabled={isSaving}
                    className={logoBgColorError ? "border-destructive" : ""}
                  />
                </div>
                <input
                  type="color"
                  value={logoBgColor || '#000000'}
                  onChange={(e) => setLogoBgColor(e.target.value)}
                  className="h-9 w-12 rounded-md border border-input cursor-pointer"
                  disabled={isSaving}
                />
              </div>
              {logoBgColorError && (
                <p className="text-sm text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {logoBgColorError}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="appName" className={appNameError ? "text-destructive" : ""}>
                <Layout className="inline-block w-4 h-4 mr-2" />
                App Name
              </Label>
              <Input
                id="appName"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                onBlur={() => handleBlur('app_name')}
                placeholder="WireGuard Mesh Manager"
                maxLength={100}
                disabled={isSaving}
                className={appNameError ? "border-destructive" : ""}
              />
              {appNameError && (
                <p className="text-sm text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {appNameError}
                </p>
              )}
            </div>

            <div>
              <Label>Preview</Label>
              <div className="mt-2 flex items-center justify-start p-6 border rounded-lg bg-muted/30">
                <div className="flex items-center space-x-2">
                  <div
                    className="h-8 w-8 rounded-md flex items-center justify-center transition-colors"
                    style={{
                      backgroundColor: logoBgColor || 'hsl(var(--sidebar-primary))',
                    }}
                  >
                    <span
                      className="text-sm font-bold"
                      style={{
                        color: logoBgColor
                          ? getContrastColor(logoBgColor)
                          : 'hsl(var(--sidebar-primary-foreground))',
                      }}
                    >
                      {logoText || 'WG'}
                    </span>
                  </div>
                  <span className="text-sidebar-foreground font-semibold text-sm">
                    {appName || 'WireGuard Mesh Manager'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <LoadingButton
            onClick={handleSave}
            loading={isSaving}
            loadingText="Saving..."
            disabled={!hasChanges || !isValidHexColor || !isValidLogoText || !isValidAppName}
          >
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
