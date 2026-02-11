import { z } from 'zod';

// Basic validation schemas
export const cidrSchema = z
  .string()
  .min(1, 'CIDR is required')
  .regex(/^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/, 'Invalid CIDR format (e.g., 192.168.1.0/24)')
  .refine(
    (cidr) => {
      const parts = cidr.split('/');
      if (parts.length !== 2) return false;
      const prefixLength = parseInt(parts[1], 10);
      return prefixLength >= 0 && prefixLength <= 32;
    },
    { message: 'CIDR prefix length must be between 0 and 32' }
  );

export const endpointSchema = z
  .string()
  .min(1, 'Endpoint is required')
  .regex(
    /^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?:(\d{1,5})$|^(\d{1,3}\.){3}\d{1,3}:(\d{1,5})$/,
    'Invalid endpoint format (e.g., example.com:51820 or 192.168.1.1:51820)'
  )
  .refine(
    (endpoint) => {
      const portPart = endpoint.split(':').pop();
      if (!portPart) return false;
      const port = parseInt(portPart, 10);
      return port >= 1 && port <= 65535;
    },
    { message: 'Port must be between 1 and 65535' }
  );

export const ipAddressSchema = z
  .string()
  .min(1, 'IP address is required')
  .regex(/^(\d{1,3}\.){3}\d{1,3}$/, 'Invalid IP address format (e.g., 192.168.1.1)')
  .refine(
    (ip) => {
      const octets = ip.split('.').map(Number);
      return octets.every((octet) => octet >= 0 && octet <= 255);
    },
    { message: 'Each octet must be between 0 and 255' }
  );

export const ipAllowlistSchema = z.array(z.string()).optional();

// Network form schema
export const createNetworkFormSchema = z.object({
  name: z.string().min(1, 'Network name is required').max(100, 'Network name must be less than 100 characters'),
  cidr: cidrSchema,
  description: z.string().max(1000, 'Description must be less than 1000 characters').optional(),
});

export type CreateNetworkFormData = z.infer<typeof createNetworkFormSchema>;

// Location form schema
export const createLocationFormSchema = z.object({
  name: z.string().min(1, 'Location name is required').max(100, 'Location name must be less than 100 characters'),
  endpoint: endpointSchema,
  description: z.string().max(1000, 'Description must be less than 1000 characters').optional(),
});

export type CreateLocationFormData = z.infer<typeof createLocationFormSchema>;

// Device form schema
export const createDeviceFormSchema = z.object({
  name: z.string().min(1, 'Device name is required').max(100, 'Device name must be less than 100 characters'),
  wireguard_ip: ipAddressSchema,
  description: z.string().max(1000, 'Description must be less than 1000 characters').optional(),
  enabled: z.boolean(),
  generate_key_pair: z.boolean(),
  ip_allowlist: ipAllowlistSchema,
});

export type CreateDeviceFormData = z.infer<typeof createDeviceFormSchema>;
