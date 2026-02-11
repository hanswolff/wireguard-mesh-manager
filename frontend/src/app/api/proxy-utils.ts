/**
 * Proxy utility for forwarding requests to backend
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

export interface ProxyRequestOptions {
  method?: Request['method'];
  headers?: HeadersInit;
  body?: BodyInit | null;
  cache?: RequestCache;
}

export async function proxyRequest(
  path: string,
  options: ProxyRequestOptions = {}
): Promise<Response> {
  // Prepend /api to all backend paths
  const apiPath = path.startsWith('/api') ? path : `/api${path}`;
  const url = `${BACKEND_URL}${apiPath}`;

  const headers = new Headers(options.headers);

  // Forward the original headers but handle content-type properly
  if (options.body && !headers.has('content-type')) {
    headers.set('content-type', 'application/json');
  }

  // Remove content-length header when forwarding body to let fetch calculate it correctly
  // This prevents RequestContentLengthMismatchError when body is consumed and re-sent
  if (options.body && headers.has('content-length')) {
    headers.delete('content-length');
  }

  const requestOptions: RequestInit = {
    method: options.method || 'GET',
    headers,
    body: options.body,
    cache: options.cache,
  };

  try {
    const response = await fetch(url, requestOptions);

    // Copy response headers, filtering out hop-by-hop headers
    const responseHeaders = new Headers();
    const hopByHopHeaders = new Set([
      'connection',
      'keep-alive',
      'transfer-encoding',
      'upgrade',
      'proxy-authenticate',
      'proxy-authorization',
      'te',
      'trailer',
      'content-encoding',
      'content-length',
    ]);

    for (const [key, value] of response.headers.entries()) {
      if (!hopByHopHeaders.has(key.toLowerCase()) && key.toLowerCase() !== 'set-cookie') {
        responseHeaders.set(key, value);
      }
    }

    const setCookieValues =
      typeof (response.headers as Headers & { getSetCookie?: () => string[] }).getSetCookie ===
      'function'
        ? (response.headers as Headers & { getSetCookie: () => string[] }).getSetCookie()
        : (() => {
            const setCookie = response.headers.get('set-cookie');
            return setCookie ? [setCookie] : [];
          })();

    for (const cookie of setCookieValues) {
      responseHeaders.append('set-cookie', cookie);
    }

    // Handle different response types
    const contentType = response.headers.get('content-type');
    let body: BodyInit | null = null;

    if (contentType?.includes('application/json')) {
      body = await response.text();
    } else if (contentType?.includes('text/')) {
      body = await response.text();
    } else {
      body = await response.blob();
    }

    return new Response(body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Proxy error to backend', {
      path,
      url,
      method: requestOptions.method,
      message: error instanceof Error ? error.message : String(error),
    });
    return new Response(
      JSON.stringify({
        error: {
          code: 'PROXY_ERROR',
          message: 'Failed to connect to backend service',
        },
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

export async function handleProxyRequest(
  request: Request,
  backendPathPrefix: string,
  pathSegments: string[] = []
): Promise<Response> {
  const path = `/${[backendPathPrefix, ...pathSegments].filter(Boolean).join('/')}`;

  // Build query string
  const url = new URL(request.url);
  const queryString = url.search;

  // Get request body for non-GET/HEAD requests
  let body: BodyInit | null = null;
  const method = request.method;
  if (
    method !== 'GET' &&
    method !== 'HEAD' &&
    request.headers.get('content-type')?.includes('application/json')
  ) {
    const jsonBody = await request.json().catch(() => null);
    body = jsonBody === null ? null : JSON.stringify(jsonBody);
  } else if (
    method !== 'GET' &&
    method !== 'HEAD' &&
    request.headers.get('content-type')?.includes('multipart/form-data')
  ) {
    body = await request.formData().catch(() => null);
  } else if (method !== 'GET' && method !== 'HEAD') {
    body = await request.text().catch(() => null);
  }

  return proxyRequest(path + queryString, {
    method,
    headers: request.headers,
    body,
  });
}
