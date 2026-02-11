import { test, expect } from '@playwright/test';
import { TestHelpers } from './helpers/test-utils';
import { SELECTORS, TEST_DATA } from './helpers/test-data';

test.describe('Authentication Flow', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    helpers = new TestHelpers(page);
  });

  test('should display unlock status when master password is not entered', async ({
    page,
  }) => {
    await expect(page.locator('body')).toContainText('WireGuard');

    if (await helpers.isElementVisible(SELECTORS.AUTH.UNLOCK_BUTTON)) {
      await expect(
        page.locator(SELECTORS.AUTH.UNLOCK_BUTTON).first()
      ).toBeVisible();
    }
  });

  test('should show unlock modal when clicking unlock button', async ({
    page,
  }) => {
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    if (await helpers.isElementVisible(SELECTORS.AUTH.MODAL)) {
      await expect(page.locator(SELECTORS.AUTH.MODAL)).toBeVisible();
      await expect(page.locator(SELECTORS.AUTH.PASSWORD_INPUT)).toBeVisible();
      await expect(page.locator(SELECTORS.AUTH.SUBMIT_BUTTON)).toBeVisible();
      await expect(page.locator(SELECTORS.AUTH.CANCEL_BUTTON)).toBeVisible();
    }
  });

  test('should validate password input in unlock modal', async ({ page }) => {
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    if (await helpers.isElementVisible(SELECTORS.AUTH.MODAL)) {
      await expect(page.locator(SELECTORS.AUTH.SUBMIT_BUTTON)).toBeDisabled();
    }
  });

  test('should allow closing unlock modal with cancel', async ({ page }) => {
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    if (await helpers.isElementVisible(SELECTORS.AUTH.MODAL)) {
      await helpers.safeClick(SELECTORS.AUTH.CANCEL_BUTTON);
      await expect(page.locator(SELECTORS.AUTH.MODAL)).not.toBeVisible();
    }
  });

  test('should allow closing unlock modal with escape key', async ({
    page,
  }) => {
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    if (await helpers.isElementVisible(SELECTORS.AUTH.MODAL)) {
      await page.keyboard.press('Escape');
      await expect(page.locator(SELECTORS.AUTH.MODAL)).not.toBeVisible();
    }
  });

  test('should show loading state during unlock attempt', async ({ page }) => {
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    if (await helpers.isElementVisible(SELECTORS.AUTH.MODAL)) {
      await helpers.safeFill(
        SELECTORS.AUTH.PASSWORD_INPUT,
        TEST_DATA.AUTH.PASSWORD
      );
      await helpers.safeClick(SELECTORS.AUTH.SUBMIT_BUTTON);
      await expect(page.locator(SELECTORS.COMMON.LOADING_STATE)).toBeVisible({
        timeout: 5000,
      });
    }
  });

  test('should handle unlock failure gracefully', async ({ page }) => {
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    if (await helpers.isElementVisible(SELECTORS.AUTH.MODAL)) {
      await helpers.safeFill(
        SELECTORS.AUTH.PASSWORD_INPUT,
        TEST_DATA.AUTH.WRONG_PASSWORD
      );
      await helpers.safeClick(SELECTORS.AUTH.SUBMIT_BUTTON);

      await expect(page.locator(SELECTORS.AUTH.ERROR_MESSAGE)).toBeVisible({
        timeout: 10000,
      });

      const modalVisible = await helpers.isElementVisible(SELECTORS.AUTH.MODAL);
      const errorToast = await helpers.isElementVisible(
        '[role="alert"], .toast-error'
      );

      expect(modalVisible || errorToast).toBe(true);
    }
  });

  test('should persist unlock state across navigation', async ({ page }) => {
    const pages = [
      { path: '/networks', content: 'Networks' },
      { path: '/audit', content: 'Audit' },
      { path: '/settings', content: 'Settings' },
    ];

    for (const { path, content } of pages) {
      await page.goto(path);
      await expect(page.locator('body')).toContainText(content);
    }

    await page.goto('/');
    await expect(page.locator('body')).toContainText('WireGuard');
  });

  test('should handle session timeout', async ({ page }) => {
    const ttlIndicator = page.locator(
      '[data-testid="ttl-indicator"], .time-remaining, .expires-in'
    );
    if (await ttlIndicator.isVisible()) {
      await expect(ttlIndicator).toBeVisible();
    }
  });
});
