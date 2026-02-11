'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface SecureTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  securePlaceholder?: string;
}

export function SecureTextarea({
  securePlaceholder,
  className,
  ...props
}: SecureTextareaProps) {
  const isSecure =
    props.name?.toLowerCase().includes('secret') ||
    props.name?.toLowerCase().includes('password') ||
    props.name?.toLowerCase().includes('key');

  // Generate random attributes to prevent autofill
  const randomId = React.useId();
  const randomName = `field_${randomId.replace(/[:\-]/g, '_')}`;

  return (
    <textarea
      {...props}
      id={props.id || randomId}
      name={props.name || randomName}
      // Disable autofill and autocompletion
      autoComplete="new-password"
      autoCorrect="off"
      autoCapitalize="off"
      spellCheck={false}
      // Add random attributes to confuse password managers
      data-form-type={randomId}
      data-lpignore="true"
      data-bv-msgfield={randomId}
      // Use secure placeholder if provided
      placeholder={
        securePlaceholder && isSecure ? securePlaceholder : props.placeholder
      }
      className={cn(
        'file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground dark:bg-input/30 border-input flex min-h-[60px] w-full rounded-md border bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
        'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]',
        'aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive',
        className
      )}
    />
  );
}
