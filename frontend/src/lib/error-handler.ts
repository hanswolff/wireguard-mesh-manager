/**
 * API Error Handling Utilities
 * Provides better error messages for different types of API errors
 */

export interface ApiError extends Error {
  status?: number;
  isUnauthorized?: boolean;
  isLocked?: boolean;
  retryAfter?: number;
}

/**
 * Check if an error is an authentication/authorization error
 */
export function isUnauthorizedError(error: unknown): error is ApiError {
  return (
    error !== null &&
    error !== undefined &&
    typeof error === 'object' &&
    ('isUnauthorized' in error
      ? (error as ApiError).isUnauthorized === true
      : 'status' in error && (error as ApiError).status === 401)
  );
}

/**
 * Check if an error is a locked error (423 - Master password locked)
 */
export function isLockedError(error: unknown): error is ApiError {
  return (
    error !== null &&
    error !== undefined &&
    typeof error === 'object' &&
    ('isLocked' in error
      ? (error as ApiError).isLocked === true
      : 'status' in error && (error as ApiError).status === 423)
  );
}

/**
 * Check if an error is a rate limit error (429)
 */
export function isRateLimitError(error: unknown): error is ApiError {
  return (
    error !== null &&
    error !== undefined &&
    typeof error === 'object' &&
    'status' in error &&
    (error as ApiError).status === 429
  );
}

/**
 * Check if an error is a server error (5xx)
 */
export function isServerError(error: unknown): error is ApiError {
  if (
    error === null ||
    error === undefined ||
    typeof error !== 'object' ||
    !('status' in error)
  ) {
    return false;
  }
  const status = (error as ApiError).status;
  return status !== undefined && status >= 500 && status < 600;
}

/**
 * Get a user-friendly error message from an API error
 */
export function getErrorMessage(error: unknown, context: string = 'operation'): string {
  // Check for 401 Unauthorized errors
  if (isUnauthorizedError(error)) {
    return 'Master password is required to access this feature. Please unlock the application first.';
  }

  // Check for 423 Locked errors (master password cache expired/locked)
  if (isLockedError(error)) {
    return 'Your session has expired or the master password cache is locked. Please unlock the application to continue.';
  }

  // Check for 403 Forbidden errors
  if (error !== null && error !== undefined && typeof error === 'object' && 'status' in error && (error as ApiError).status === 403) {
    return 'You do not have permission to perform this action.';
  }

  // Check for 404 Not Found errors
  if (error !== null && error !== undefined && typeof error === 'object' && 'status' in error && (error as ApiError).status === 404) {
    return `The requested ${context.toLowerCase()} was not found.`;
  }

  // Check for 429 Rate Limit errors
  if (isRateLimitError(error)) {
    const retryAfter = (error as ApiError).retryAfter;
    const retryMessage = retryAfter
      ? ` Please wait ${retryAfter} seconds before trying again.`
      : ' Please try again later.';
    return `Too many requests.${retryMessage}`;
  }

  // Check for 5xx Server errors
  if (isServerError(error)) {
    return `Server error while processing ${context.toLowerCase()}. Please try again.`;
  }

  // Check for network/connection errors
  if (error instanceof Error) {
    const message = error.message.toLowerCase();

    if (message.includes('failed to fetch') || message.includes('network')) {
      return 'Network error: Unable to connect to the server. Please check your connection.';
    }

    if (message.includes('timeout')) {
      return 'Request timeout: The server took too long to respond. Please try again.';
    }
  }

  // Default: return the error message if it's an Error
  if (error instanceof Error) {
    return error.message;
  }

  // Fallback
  return `An error occurred while processing your request.`;
}

/**
 * Get error title for display
 */
export function getErrorTitle(error: unknown): string {
  if (isUnauthorizedError(error)) {
    return 'Master Password Required';
  }

  if (isLockedError(error)) {
    return 'Session Expired';
  }

  if (isRateLimitError(error)) {
    return 'Rate Limit Exceeded';
  }

  if (error !== null && error !== undefined && typeof error === 'object' && 'status' in error) {
    const status = (error as ApiError).status;

    if (status !== undefined) {
      if (status === 403) return 'Access Denied';
      if (status === 404) return 'Not Found';
      if (status >= 500) return 'Server Error';
      if (status >= 400) return 'Request Error';
    }
  }

  return 'Something Went Wrong';
}
