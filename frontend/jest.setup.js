global.IS_REACT_ACT_ENVIRONMENT = true;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

require('@testing-library/jest-dom');
require('jest-axe/extend-expect');
const { TransformStream } = require('node:stream/web');

const originalConsoleError = console.error;
console.error = (...args) => {
  const message = args[0];
  if (
    typeof message === 'string' &&
    message.includes(
      'The current testing environment is not configured to support act'
    )
  ) {
    return;
  }
  originalConsoleError(...args);
};

if (typeof window !== 'undefined') {
  window.IS_REACT_ACT_ENVIRONMENT = true;

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
}

// Polyfill for TransformStream (required in Node.js environment)
if (typeof globalThis.TransformStream === 'undefined') {
  globalThis.TransformStream = TransformStream;
}

if (typeof HTMLCanvasElement !== 'undefined') {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value: () => null,
    writable: true,
    configurable: true,
  });
}

if (typeof window !== 'undefined' && typeof window.ResizeObserver === 'undefined') {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  window.ResizeObserver = ResizeObserver;
  global.ResizeObserver = ResizeObserver;
}

if (typeof global.fetch === 'undefined') {
  global.fetch = jest.fn(async (input) => {
    const url = typeof input === 'string' ? input : input.url;
    const isUnlockStatus = url.includes('/master-password/is-unlocked');
    const payload = isUnlockStatus ? { is_unlocked: false } : {};
    return {
      ok: true,
      json: async () => payload,
      text: async () => JSON.stringify(payload),
      headers: new Headers({ 'content-type': 'application/json' }),
    };
  });
}
