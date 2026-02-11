/**
 * Utility functions for CIDR (Classless Inter-Domain Routing) operations
 */

/**
 * Converts an IP address string to a 32-bit integer
 * @param ip - IP address in dotted decimal notation (e.g., "192.168.1.1")
 * @returns 32-bit integer representation of the IP address
 */
export function ipToNumber(ip: string): number {
  return ip.split('.').reduce((acc, octet) => (acc << 8) + parseInt(octet, 10), 0) >>> 0;
}

/**
 * Converts a 32-bit integer to an IP address string
 * @param num - 32-bit integer representation of an IP address
 * @returns IP address in dotted decimal notation
 */
export function numberToIp(num: number): string {
  return [
    (num >>> 24) & 255,
    (num >>> 16) & 255,
    (num >>> 8) & 255,
    num & 255,
  ].join('.');
}

/**
 * Checks if an IP address is within a CIDR range
 * @param ip - IP address to check (e.g., "192.168.1.100")
 * @param cidr - CIDR notation (e.g., "192.168.1.0/24")
 * @returns true if IP is within the CIDR range, false otherwise
 */
export function isIpInCidr(ip: string, cidr: string): boolean {
  const [networkAddress, prefixLengthStr] = cidr.split('/');
  const prefixLength = parseInt(prefixLengthStr, 10);

  if (isNaN(prefixLength) || prefixLength < 0 || prefixLength > 32) {
    return false;
  }

  const ipNum = ipToNumber(ip);
  const networkNum = ipToNumber(networkAddress);

  // Create a mask for the prefix length
  const mask = 0xffffffff << (32 - prefixLength) >>> 0;

  // Check if IP is within the network
  return (ipNum & mask) === (networkNum & mask);
}

/**
 * Parses a CIDR string into its components
 * @param cidr - CIDR notation (e.g., "192.168.1.0/24")
 * @returns Object with network address, prefix length, and broadcast address
 */
export function parseCidr(cidr: string): {
  networkAddress: string;
  prefixLength: number;
  broadcastAddress: string;
  firstUsableIp: string;
  lastUsableIp: string;
} | null {
  const [networkAddress, prefixLengthStr] = cidr.split('/');
  const prefixLength = parseInt(prefixLengthStr, 10);

  if (isNaN(prefixLength) || prefixLength < 0 || prefixLength > 32) {
    return null;
  }

  const networkNum = ipToNumber(networkAddress);
  const mask = 0xffffffff << (32 - prefixLength) >>> 0;

  const network = networkNum & mask;
  const broadcast = network | (~mask >>> 0);

  // For /31 and /32 networks, special handling
  let firstUsable: number;
  let lastUsable: number;

  if (prefixLength === 32) {
    firstUsable = network;
    lastUsable = network;
  } else if (prefixLength === 31) {
    firstUsable = network;
    lastUsable = broadcast;
  } else {
    firstUsable = network + 1;
    lastUsable = broadcast - 1;
  }

  return {
    networkAddress: numberToIp(network),
    prefixLength,
    broadcastAddress: numberToIp(broadcast),
    firstUsableIp: numberToIp(firstUsable),
    lastUsableIp: numberToIp(lastUsable),
  };
}
