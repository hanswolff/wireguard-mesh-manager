export const TEST_DATA = {
  NETWORK: {
    NAME: 'Test Network',
    CIDR: '10.0.0.0/24',
    UPDATED_NAME: 'Updated Network Name',
  },
  LOCATION: {
    NAME: 'Test Location',
    ENDPOINT: 'test.example.com:51820',
    INVALID_ENDPOINT: 'invalid-endpoint',
  },
  DEVICE: {
    NAME: 'Test Device',
  },
  AUTH: {
    PASSWORD: 'test-password', // pragma: allowlist secret
    WRONG_PASSWORD: 'wrong-password', // pragma: allowlist secret
  },
} as const;

export const SELECTORS = {
  AUTH: {
    UNLOCK_BUTTON:
      '[data-testid="unlock-status-button"], button:has-text("Unlock"), button:has-text("Locked")',
    MODAL:
      '[role="dialog"], .modal, [data-testid="master-password-unlock-modal"]',
    PASSWORD_INPUT: 'input[type="password"]',
    SUBMIT_BUTTON:
      '[role="dialog"] button[type="submit"], [role="dialog"] button:has-text("Unlock")',
    CANCEL_BUTTON: 'button:has-text("Cancel")',
    ERROR_MESSAGE:
      '[role="dialog"] [role="alert"], [role="dialog"] [data-slot="alert"], [role="dialog"] .error, [role="dialog"] .error-message',
  },
  NETWORK: {
    ITEM: '[data-testid="network-item"], .network-card, tr:has(td)',
    CREATE_BUTTON:
      'button:has-text("Create"), button:has-text("Add Network"), a:has-text("New")',
    NAME_INPUT: 'input[name*="name"], input[placeholder*="name"]',
    CIDR_INPUT: 'input[name*="cidr"], input[placeholder*="CIDR"]',
    EDIT_BUTTON:
      'button:has-text("Edit"), button[aria-label*="edit"], [data-testid="edit-button"]',
    DELETE_BUTTON:
      'button:has-text("Delete"), button[aria-label*="delete"], [data-testid="delete-button"]',
    SAVE_BUTTON:
      'button:has-text("Save"), button:has-text("Update"), button[type="submit"]',
  },
  LOCATION: {
    ITEM: '[data-testid="location-item"], .location-card, .location-row',
    SECTION:
      'h2:has-text("Locations"), section:has-text("Locations"), [data-testid="locations-section"]',
    ADD_BUTTON:
      'button:has-text("Add Location"), button:has-text("Create Location")',
    NAME_INPUT: 'input[name*="name"], input[placeholder*="name"]',
    ENDPOINT_INPUT: 'input[name*="endpoint"], input[placeholder*="endpoint"]',
  },
  DEVICE: {
    ITEM: '[data-testid="device-item"], .device-card, tr:has(td)',
    SECTION:
      'h2:has-text("Devices"), section:has-text("Devices"), [data-testid="devices-section"]',
    ADD_BUTTON:
      'button:has-text("Add Device"), button:has-text("Create Device")',
    DETAILS: '[data-testid="device-details"], .device-detail-section',
    API_KEY_SECTION:
      '[data-testid="api-key-section"], section:has-text("API Key"]',
  },
  CONFIG: {
    PREVIEW:
      '[data-testid="config-preview"], section:has-text("Config"), .config-section',
    DOWNLOAD_BUTTON:
      'button:has-text("Download"), button:has-text("Export"), [data-testid="download-config"]',
    COPY_BUTTON:
      'button:has-text("Copy"), button[aria-label*="copy"], [data-testid="copy-config"]',
  },
  AUDIT: {
    EVENTS_LIST: '[data-testid="audit-events"], .audit-list, table tbody',
    EVENT_ROW: 'tr, [data-testid="audit-event"], .audit-item',
    SEARCH_INPUT:
      'input[placeholder*="search"], input[name*="search"], [data-testid="search-input"]',
    FILTER_SELECT: 'select[name*="filter"], [data-testid="filter-select"]',
    EXPORT_BUTTON: 'button:has-text("Export"), [data-testid="export-audit"]',
    PAGINATION:
      '.pagination, nav[aria-label*="pagination"], [data-testid="pagination"]',
    NEXT_PAGE:
      'button:has-text("Next"), a[aria-label*="next"], [data-testid="next-page"]',
    LIVE_INDICATOR:
      '[data-testid="live-indicator"], .live-indicator, .real-time-status',
  },
  SETTINGS: {
    SECTION: 'section, .settings-section, [data-testid="settings-section"]',
    TRUSTED_PROXY:
      '[data-testid="trusted-proxy"], label:has-text("Trusted Proxy")',
    CORS_ORIGINS: '[data-testid="cors-origins"], label:has-text("CORS")',
    RATE_LIMITS: '[data-testid="rate-limits"], label:has-text("Rate Limit")',
    SAVE_BUTTON:
      'button:has-text("Save"), button[type="submit"], [data-testid="save-settings"]',
    BACKUP_SECTION:
      '[data-testid="backup-settings"], section:has-text("Backup"), .backup-section',
  },
  KEY_ROTATION: {
    START_BUTTON:
      'button:has-text("Start Rotation"), button:has-text("Rotate Keys"), [data-testid="start-rotation"]',
    CANCEL_BUTTON:
      'button:has-text("Cancel"), button:has-text("Stop"), [data-testid="cancel-rotation"]',
    PROGRESS_SECTION:
      '[data-testid="rotation-progress"], .progress-section, .rotation-status',
    PROGRESS_BAR:
      '.progress, [role="progressbar"], [data-testid="progress-bar"]',
    STATUS_TEXT: '[data-testid="status-text"], .status-message',
    COMPLETION_SECTION:
      '[data-testid="rotation-complete"], .completion-section, .rotation-summary',
    ROTATED_COUNT: '[data-testid="rotated-count"], .items-rotated',
  },
  COMMON: {
    SUCCESS_MESSAGE:
      '.success, .toast-success, [data-testid="success-message"]',
    ERROR_MESSAGE:
      '.error, .error-message, [data-invalid], [aria-invalid="true"]',
    LOADING_STATE: '.loading, .spinner, [disabled], button:disabled',
    MODAL: '[role="dialog"], .modal',
    CONFIRM_DIALOG: '[role="dialog"], .modal, .confirmation-dialog',
    SEARCH_INPUT:
      'input[placeholder*="search"], input[name*="search"], [data-testid="search-input"]',
    SORT_SELECT:
      'select[name*="sort"], [data-testid="sort-select"], .sort-control',
    SIDEBAR: '[data-testid="sidebar"], nav[role="navigation"], .side-nav',
    MOBILE_MENU:
      '[data-testid="mobile-menu"], button[aria-label*="menu"], .hamburger',
    EMPTY_STATE: '.empty-state, [data-testid="empty-state"], .no-data',
  },
} as const;
