export type ExportFormat = 'wg' | 'json' | 'mobile';

export interface FormatOption {
  value: ExportFormat;
  label: string;
  title: string;
  description: string;
}

export const FORMAT_OPTIONS: FormatOption[] = [
  {
    value: 'wg',
    label: 'WireGuard Config (.conf)',
    title: 'WireGuard Config',
    description: 'Standard WireGuard configuration file for Linux/macOS',
  },
  {
    value: 'json',
    label: 'JSON Export',
    title: 'JSON Export',
    description: 'Complete network and device data in JSON format',
  },
  {
    value: 'mobile',
    label: 'Mobile QR Code',
    title: 'Mobile QR Code',
    description: 'QR code format for mobile WireGuard apps',
  },
];

/**
 * Download a file with given content (string or Blob) and filename
 */
export function downloadFile(content: string | Blob, filename: string, contentType: string = 'text/plain'): void {
  let blob: Blob;
  
  if (content instanceof Blob) {
    blob = content;
  } else {
    blob = new Blob([content], { type: contentType });
  }
  
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Get the master password from cache or return empty string
 * This is used to decrypt private keys during config export
 * The backend handles actual encryption/decryption
 */
export function getMasterPassword(): string {
  // In a real implementation, the master password would be retrieved from
  // a secure cache after the user unlocks it with the master password modal
  // For now, we return an empty string and let the backend handle decryption
  return '';
}

/**
 * Generate an export filename based on the network name and format
 */
export function generateExportFilename(networkName: string, format: ExportFormat): string {
  const sanitized = networkName.replace(/[^a-zA-Z0-9_-]/g, '_');
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  
  const extensions: Record<ExportFormat, string> = {
    wg: 'conf',
    json: 'json',
    mobile: 'json',
  };
  
  return `${sanitized}_${timestamp}.${extensions[format]}`;
}
