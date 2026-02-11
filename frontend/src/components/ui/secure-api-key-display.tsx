'use client';

import * as React from 'react';
import {
  Copy,
  Eye,
  EyeOff,
  Check,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { useCopyToClipboard } from '@/app/networks/[id]/devices/[deviceId]/use-copy-to-clipboard';

interface SecureApiKeyDisplayProps {
  apiKey: string;
  label?: string;
  description?: string;
  showRefreshButton?: boolean;
  onRefreshKey?: () => void;
  className?: string;
}

export function SecureApiKeyDisplay({
  apiKey,
  label = 'API Key',
  description,
  showRefreshButton = false,
  onRefreshKey,
  className,
}: SecureApiKeyDisplayProps) {
  const [isRevealed, setIsRevealed] = useState(false);
  const [hasBeenShown, setHasBeenShown] = useState(false);
  const [copyWarningShown, setCopyWarningShown] = useState(false);
  const { copyToClipboard, isCopied } = useCopyToClipboard();

  useEffect(() => {
    if (!copyWarningShown) return;

    const timeout = setTimeout(() => setCopyWarningShown(false), 5000);

    return () => clearTimeout(timeout);
  }, [copyWarningShown]);

  const handleReveal = () => {
    setIsRevealed(true);
    setHasBeenShown(true);
  };

  const handleHide = () => {
    setIsRevealed(false);
  };

  const handleCopy = async () => {
    await copyToClipboard(apiKey, 'API Key');
    setCopyWarningShown(true);
  };

  const maskKey = (key: string) => {
    if (!key) return '';
    if (key.length <= 8) return '*'.repeat(key.length);
    const visibleChars = 4;
    const maskedPart = '*'.repeat(Math.max(1, key.length - visibleChars * 2));
    return (
      key.substring(0, visibleChars) +
      maskedPart +
      key.substring(key.length - visibleChars)
    );
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">{label}</h3>
          {description && (
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
          )}
        </div>
        {hasBeenShown && (
          <Badge variant="secondary" className="text-xs">
            <Eye className="h-3 w-3 mr-1" />
            Revealed
          </Badge>
        )}
      </div>

      {/* API Key Display */}
      <div className="relative">
        <div className="flex items-center gap-2 p-3 bg-muted/30 rounded-md border font-mono text-sm">
          <span className="flex-1 select-none">
            {isRevealed ? apiKey : maskKey(apiKey)}
          </span>

          {/* Reveal/Hide Button */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={isRevealed ? handleHide : handleReveal}
            className="h-7 px-2"
          >
            {isRevealed ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
            <span className="sr-only">
              {isRevealed ? 'Hide' : 'Reveal'} API key
            </span>
          </Button>

          {/* Copy Button */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            disabled={!isRevealed}
            className="h-7 px-2"
          >
            {isCopied ? (
              <Check className="h-4 w-4 text-success" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
            <span className="sr-only">Copy API key</span>
          </Button>

          {/* Refresh Button */}
          {showRefreshButton && onRefreshKey && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onRefreshKey}
              className="h-7 px-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="sr-only">Regenerate API key</span>
            </Button>
          )}
        </div>
      </div>

      {/* Copy Warning */}
      {copyWarningShown && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="text-xs">
            API key copied to clipboard. Store it securely immediately - it
            won&apos;t be shown again.
          </AlertDescription>
        </Alert>
      )}

      {/* Security Notice */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="text-xs">
          <strong>Security notice:</strong> API keys are sensitive credentials.
          {hasBeenShown
            ? ' This key has been revealed and should be stored securely.'
            : ' Click the eye icon to reveal the full key.'}
          Never share API keys or commit them to version control.
        </AlertDescription>
      </Alert>

      {/* Hidden after first view behavior */}
      {hasBeenShown && !isRevealed && (
        <div className="p-3 bg-muted/50 rounded-md border border-border">
          <div className="flex items-center gap-2">
            <EyeOff className="h-4 w-4 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">
              For security, the API key is now masked. Click the eye icon to
              reveal it again if needed.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
