'use client';

import * as React from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface SecureInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  showPasswordToggle?: boolean;
  securePlaceholder?: string;
}

export function SecureInput({
  type,
  showPasswordToggle = type === 'password' || type === 'api-key',
  securePlaceholder,
  className,
  ...props
}: SecureInputProps) {
  const [showValue, setShowValue] = useState(false);
  const [inputType, setInputType] = useState(type);

  const isSecure =
    type === 'password' || type === 'api-key' || type === 'secret';

  const toggleVisibility = () => {
    setShowValue(!showValue);
    setInputType(showValue ? type : 'text');
  };

  // Generate random attributes to prevent autofill
  const randomId = React.useId();
  const randomName = `field_${randomId.replace(/[:\-]/g, '_')}`;

  return (
    <div className="relative">
      <input
        {...props}
        type={inputType}
        id={props.id || randomId}
        name={props.name || randomName}
        // Disable autofill
        autoComplete="new-password"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        // Add random attributes to confuse password managers
        data-form-type={randomId}
        data-lpignore="true"
        data-bv-msgfield={randomId}
        // Use secure placeholder if provided and field is secure
        placeholder={
          securePlaceholder && isSecure && !showValue
            ? securePlaceholder
            : props.placeholder
        }
        className={cn('pr-10', className)}
      />

      {/* Password visibility toggle for secure fields */}
      {showPasswordToggle && isSecure && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="absolute right-0 top-0 h-full px-3 py-2"
          onClick={toggleVisibility}
          tabIndex={-1}
        >
          {showValue ? (
            <EyeOff className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Eye className="h-4 w-4 text-muted-foreground" />
          )}
          <span className="sr-only">
            {showValue ? 'Hide' : 'Show'}{' '}
            {type === 'password' ? 'password' : 'value'}
          </span>
        </Button>
      )}
    </div>
  );
}
