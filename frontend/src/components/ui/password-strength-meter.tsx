'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  apiClient,
  type PasswordStrengthValidation,
  type PasswordPolicy,
} from '@/lib/api-client';

interface PasswordStrengthMeterProps {
  password: string;
  onValidationChange?: (isValid: boolean) => void;
  showPolicy?: boolean;
}

export function PasswordStrengthMeter({
  password,
  onValidationChange,
  showPolicy = true,
}: PasswordStrengthMeterProps) {
  const [validation, setValidation] =
    useState<PasswordStrengthValidation | null>(null);
  const [policy, setPolicy] = useState<PasswordPolicy | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [isValidating, setIsValidating] = useState(false);

  useEffect(() => {
    loadPasswordPolicy();
  }, []);

  useEffect(() => {
    if (password) {
      validatePassword(password);
    } else {
      setValidation(null);
      onValidationChange?.(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [password]);

  const loadPasswordPolicy = async () => {
    try {
      const policyData = await apiClient.getPasswordPolicy();
      setPolicy(policyData);
    } catch (error) {
      console.error('Failed to load password policy:', error);
    }
  };

  const validatePassword = async (pwd: string) => {
    setIsValidating(true);
    try {
      const result = await apiClient.validatePassword(pwd);
      setValidation(result);
      onValidationChange?.(result.is_valid);
    } catch (error) {
      console.error('Failed to validate password:', error);
      setValidation(null);
      onValidationChange?.(false);
    } finally {
      setIsValidating(false);
    }
  };

  const strengthStyles = {
    0: { label: 'Very Weak', tone: 'destructive' },
    1: { label: 'Weak', tone: 'warning' },
    2: { label: 'Fair', tone: 'info' },
    3: { label: 'Good', tone: 'success' },
    4: { label: 'Strong', tone: 'success' },
  } as const;

  const toneStyles: Record<
    (typeof strengthStyles)[keyof typeof strengthStyles]['tone'],
    { text: string; badge: string; bar: string }
  > = {
    destructive: {
      text: 'text-destructive',
      badge:
        'bg-destructive-surface text-destructive-foreground border-destructive-border',
      bar: 'bg-destructive',
    },
    warning: {
      text: 'text-warning-foreground',
      badge: 'bg-warning-surface text-warning-foreground border-warning-border',
      bar: 'bg-warning',
    },
    info: {
      text: 'text-info-foreground',
      badge: 'bg-info-surface text-info-foreground border-info-border',
      bar: 'bg-info',
    },
    success: {
      text: 'text-success',
      badge: 'bg-success-surface text-success-foreground border-success-border',
      bar: 'bg-success',
    },
  };

  const getStrengthStyle = (strength: number) => {
    const fallback = strengthStyles[0];
    const style =
      strengthStyles[strength as keyof typeof strengthStyles] || fallback;
    return { ...style, ...toneStyles[style.tone] };
  };

  if (!password && !showPolicy) {
    return null;
  }

  const strengthStyle = getStrengthStyle(validation?.strength ?? 0);

  return (
    <div className="space-y-3">
      {password && (
        <>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Password Strength</span>
              {validation && (
                <Badge
                  variant="outline"
                  className={`${strengthStyle.badge} border`}
                >
                  {strengthStyle.label}
                </Badge>
              )}
            </div>
            <Progress
              value={validation?.score || 0}
              className="h-2"
              indicatorClassName={strengthStyle.bar}
            />
            {validation && (
              <p className="text-xs text-muted-foreground">
                Score: {validation.score}/100
              </p>
            )}
          </div>

          {validation && validation.feedback.length > 0 && (
            <Alert variant={validation.is_valid ? 'default' : 'destructive'}>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-1">
                  <p className={`font-medium ${strengthStyle.text}`}>
                    {validation.is_valid
                      ? 'Password meets requirements'
                      : 'Password needs improvement:'}
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {validation.feedback.map((feedback, index) => (
                      <li key={index}>{feedback}</li>
                    ))}
                  </ul>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </>
      )}

      {showPolicy && policy && (
        <div className="rounded-md border p-3 bg-muted/30">
          <h4 className="text-sm font-medium mb-2">Password Requirements:</h4>
          <ul className="space-y-1 text-xs text-muted-foreground">
            {policy.requirements.map((requirement, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2">•</span>
                <span>{requirement}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
