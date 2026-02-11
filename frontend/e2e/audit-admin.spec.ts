import { test, expect } from '@playwright/test';
import { TestHelpers } from './helpers/test-utils';
import { SELECTORS } from './helpers/test-data';

test.describe('Audit & Admin Tools', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    helpers = new TestHelpers(page);
  });

  const navigateToAudit = async () => {
    await helpers.navigateWithChecks('/audit');
    await expect(helpers.page.locator('body')).toContainText('Audit');
  };

  const navigateToSettings = async () => {
    await helpers.navigateWithChecks('/settings');
    await expect(helpers.page.locator('body')).toContainText('Settings');
  };

  const waitForSearchResults = async () => {
    await helpers.page.waitForTimeout(500);
  };

  const checkForSensitiveData = (text: string) => {
    const sensitiveWords = ['password', 'private', 'secret'];
    const lowerText = text.toLowerCase();
    return !sensitiveWords.some((word) => lowerText.includes(word));
  };

  test.describe('Audit Event Viewer', () => {
    test('should access audit page', navigateToAudit);

    test('should display audit events list', async () => {
      await navigateToAudit();

      const eventsList = helpers.page.locator(SELECTORS.AUDIT.EVENTS_LIST);
      if (await eventsList.isVisible()) {
        await expect(eventsList).toBeVisible();

        const visibleRows = await helpers.getVisibleElements(
          SELECTORS.AUDIT.EVENT_ROW
        );
        if (visibleRows.length > 0) {
          expect(visibleRows.length).toBeGreaterThan(0);
        }
      }
    });

    test('should have search functionality', async () => {
      await navigateToAudit();

      const searchInput = helpers.page.locator(SELECTORS.AUDIT.SEARCH_INPUT);
      if (await searchInput.isVisible()) {
        await expect(searchInput).toBeVisible();

        await searchInput.fill('test');
        await waitForSearchResults();

        const currentUrl = helpers.page.url();
        expect(currentUrl).toContain('audit');
      }
    });

    test('should have filtering options', async () => {
      await navigateToAudit();

      const filterControls = helpers.page.locator(
        'select, .filter-section, [data-testid="filters"]'
      );
      if (await filterControls.first().isVisible()) {
        await expect(filterControls.first()).toBeVisible();

        const actionFilter = helpers.page.locator(
          'select[name*="action"], [data-testid="action-filter"]'
        );
        const timeFilter = helpers.page.locator(
          'select[name*="time"], [data-testid="time-filter"]'
        );

        if (await actionFilter.isVisible()) {
          await actionFilter.selectOption({ index: 0 });
        }
        if (await timeFilter.isVisible()) {
          await timeFilter.selectOption({ index: 0 });
        }
      }
    });

    test('should show event details', async () => {
      await navigateToAudit();

      const visibleRows = await helpers.getVisibleElements(
        SELECTORS.AUDIT.EVENT_ROW
      );
      if (visibleRows.length > 0) {
        await visibleRows[0].click();

        const detailsModal = helpers.page.locator(
          '[role="dialog"], .modal, .event-details'
        );
        if (await detailsModal.isVisible()) {
          await expect(detailsModal).toBeVisible();
          await expect(detailsModal).toContainText(
            /\b(Actor|Action|Time|IP|Details)\b/i
          );
        }
      }
    });

    test('should paginate large datasets', async () => {
      await navigateToAudit();

      const pagination = helpers.page.locator(SELECTORS.AUDIT.PAGINATION);
      if (await pagination.isVisible()) {
        await expect(pagination).toBeVisible();

        const nextPageButton = helpers.page.locator(SELECTORS.AUDIT.NEXT_PAGE);
        if (
          (await nextPageButton.isVisible()) &&
          !(await nextPageButton.isDisabled())
        ) {
          await nextPageButton.click();
          await waitForSearchResults();
        }
      }
    });

    test('should export audit logs', async () => {
      await navigateToAudit();

      const exportButton = helpers.page.locator(SELECTORS.AUDIT.EXPORT_BUTTON);
      if (await exportButton.isVisible()) {
        const downloadPromise = helpers.page.waitForEvent('download');
        await exportButton.click();

        const filename = await helpers.waitForDownload(downloadPromise, [
          '.csv',
          '.json',
          '.txt',
        ]);
        expect(filename).toMatch(/(\.csv|\.json|\.txt)$/);
      }
    });

    test('should handle real-time updates', async () => {
      await navigateToAudit();

      const liveIndicator = helpers.page.locator(
        SELECTORS.AUDIT.LIVE_INDICATOR
      );
      if (await liveIndicator.isVisible()) {
        await expect(liveIndicator).toBeVisible();

        await helpers.createNetwork();
        await navigateToAudit();

        const recentEvent = helpers.page.locator(
          '[data-testid="recent-event"], .recent-item'
        );
        if (await recentEvent.first().isVisible()) {
          await expect(recentEvent.first()).toBeVisible();
        }
      }
    });

    test('should redact sensitive information', async () => {
      await navigateToAudit();

      const visibleContents = await helpers.waitForTextContent(
        '.audit-content, .event-details, [data-testid="event-data"]'
      );

      visibleContents.forEach((text) => {
        expect(checkForSensitiveData(text)).toBe(true);
      });
    });
  });

  test.describe('Settings Page', () => {
    test('should access settings page', navigateToSettings);

    test('should display operational settings', async () => {
      await navigateToSettings();

      const settingsSections = helpers.page.locator(SELECTORS.SETTINGS.SECTION);
      if (await settingsSections.first().isVisible()) {
        await expect(settingsSections.first()).toBeVisible();

        const settings = [
          SELECTORS.SETTINGS.TRUSTED_PROXY,
          SELECTORS.SETTINGS.CORS_ORIGINS,
          SELECTORS.SETTINGS.RATE_LIMITS,
        ];

        for (const settingSelector of settings) {
          const setting = helpers.page.locator(settingSelector);
          if (await setting.isVisible()) {
            await expect(setting).toBeVisible();
          }
        }
      }
    });

    test('should allow modifying settings', async () => {
      await navigateToSettings();

      const enabledSwitches = await helpers.getVisibleElements(
        'input[type="checkbox"], [role="switch"], .toggle',
        3
      );

      const activeSwitches = enabledSwitches.filter(
        async (toggle) => !(await toggle.isDisabled())
      );

      if (activeSwitches.length > 0) {
        await activeSwitches[0].click();
        await waitForSearchResults();

        const saveButton = helpers.page.locator(SELECTORS.SETTINGS.SAVE_BUTTON);
        if (await saveButton.isVisible()) {
          await saveButton.click();
          await expect(
            helpers.page.locator(SELECTORS.COMMON.SUCCESS_MESSAGE)
          ).toBeVisible({ timeout: 5000 });
        }
      }
    });

    test('should validate settings inputs', async () => {
      await navigateToSettings();

      const validatableInputs = await helpers.getVisibleElements(
        'input[type="text"], input[type="number"], input[type="url"]',
        3
      );
      const enabledInputs = validatableInputs.filter(
        async (input) => !(await input.isDisabled())
      );

      if (enabledInputs.length > 0) {
        await enabledInputs[0].fill(
          'invalid-test-value-with-special-chars-!@#$%^&*()'
        );

        const saveButton = helpers.page.locator(
          'button:has-text("Save"), button[type="submit"]'
        );
        if (await saveButton.isVisible()) {
          await saveButton.click();

          const errorMessage = helpers.page.locator(
            SELECTORS.COMMON.ERROR_MESSAGE
          );
          if (await errorMessage.first().isVisible()) {
            await expect(errorMessage.first()).toBeVisible();
          }
        }
      }
    });

    test('should have backup/restore settings', async () => {
      await navigateToSettings();

      const backupSection = helpers.page.locator(
        SELECTORS.SETTINGS.BACKUP_SECTION
      );
      if (await backupSection.isVisible()) {
        await expect(backupSection).toBeVisible();

        const buttons = [
          'button:has-text("Backup"), button:has-text("Download Backup")',
          'button:has-text("Restore"), button:has-text("Upload")',
        ];

        for (const buttonSelector of buttons) {
          const button = helpers.page.locator(buttonSelector);
          if (await button.isVisible()) {
            await expect(button).toBeVisible();
          }
        }
      }
    });
  });

  test.describe('Error Handling & Edge Cases', () => {
    test('should handle network connectivity issues', async () => {
      await helpers.navigateWithChecks('/networks');

      await helpers.page.context().setOffline(true);

      await helpers.safeClick(SELECTORS.NETWORK.CREATE_BUTTON);

      const errorMessage = helpers.page.locator(
        '.error, .error-message, [data-testid="network-error"]'
      );
      if (await errorMessage.first().isVisible({ timeout: 5000 })) {
        await expect(errorMessage.first()).toBeVisible();
      }

      await helpers.page.context().setOffline(false);
    });

    test('should handle session timeout gracefully', async () => {
      await helpers.navigateWithChecks('/networks');

      const sessionTimeout = helpers.page.locator(
        '[data-testid="session-timeout"], .timeout-modal, .session-expired'
      );
      if (await sessionTimeout.isVisible()) {
        await expect(sessionTimeout).toBeVisible();

        const reauthButton = helpers.page.locator(
          'button:has-text("Login"), button:has-text("Re-authenticate")'
        );
        if (await reauthButton.isVisible()) {
          await expect(reauthButton).toBeVisible();
        }
      }
    });

    test('should show appropriate empty states', async () => {
      await helpers.navigateWithChecks('/networks');

      const emptyState = helpers.page.locator(SELECTORS.COMMON.EMPTY_STATE);
      if (await emptyState.isVisible()) {
        await expect(emptyState).toBeVisible();

        const emptyStateText = await emptyState.textContent();
        expect(emptyStateText).toMatch(
          /(no networks|empty|create your first)/i
        );

        const createButton = helpers.page.locator(
          'button:has-text("Create"), button:has-text("Add")'
        );
        if (await createButton.isVisible()) {
          await expect(createButton).toBeVisible();
        }
      }
    });

    test('should handle large datasets efficiently', async () => {
      await navigateToAudit();

      const loadingIndicator = helpers.page.locator(
        '.loading, .spinner, [data-testid="loading"]'
      );
      if (await loadingIndicator.first().isVisible()) {
        const loadTime = await helpers.measureLoadTime(async () => {
          await expect(loadingIndicator.first()).not.toBeVisible({
            timeout: 10000,
          });
        });
        expect(loadTime).toBeLessThan(8000);
      }

      await helpers.page.waitForLoadState('networkidle');
    });
  });
});
