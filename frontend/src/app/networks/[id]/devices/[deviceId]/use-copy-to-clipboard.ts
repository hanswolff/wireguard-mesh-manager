import { useState, useCallback, useEffect } from 'react';
import { toast } from '@/components/ui/use-toast';

const COPIED_FEEDBACK_TIMEOUT = 2000;

export function useCopyToClipboard() {
  const [copiedType, setCopiedType] = useState<string | null>(null);

  const copyToClipboard = useCallback(async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: 'Copied',
        description: `${type} copied to clipboard`,
      });

      if (type === 'API Key') {
        setCopiedType(type);
      }
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to copy to clipboard',
        variant: 'destructive',
      });
    }
  }, []);

  useEffect(() => {
    if (!copiedType) return;

    const timeout = setTimeout(() => setCopiedType(null), COPIED_FEEDBACK_TIMEOUT);

    return () => clearTimeout(timeout);
  }, [copiedType]);

  return { copyToClipboard, isCopied: copiedType === 'API Key' };
}
