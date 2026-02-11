import { test, expect } from '@playwright/test';
import { TestHelpers } from '../helpers/test-utils';
import { SELECTORS, TEST_DATA } from '../helpers/test-data';

test.describe('TestHelpers Utility Class', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    helpers = new TestHelpers(page);
  });

  test('should initialize correctly', () => {
    expect(helpers).toBeDefined();
    expect(helpers.page).toBeDefined();
  });

  test('should check element visibility correctly', async () => {
    const isVisible = await helpers.isElementVisible('body');
    expect(isVisible).toBe(true);
  });

  test('should handle safe click correctly', async () => {
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    const isModalVisible = await helpers.isElementVisible(SELECTORS.AUTH.MODAL);
    expect(isModalVisible).toBe(true);
  });

  test('should navigate with checks', async () => {
    await helpers.navigateWithChecks('/networks');
    expect(helpers.page.url()).toContain('/networks');
  });

  test('should handle safe fill correctly', async ({ page }) => {
    await page.goto('/');
    await helpers.safeClick(SELECTORS.AUTH.UNLOCK_BUTTON);

    const modalVisible = await helpers.isElementVisible(SELECTORS.AUTH.MODAL);
    if (modalVisible) {
      await helpers.safeFill(
        SELECTORS.AUTH.PASSWORD_INPUT,
        TEST_DATA.AUTH.PASSWORD
      );
      const passwordInput = page.locator(SELECTORS.AUTH.PASSWORD_INPUT);
      const value = await passwordInput.inputValue();
      expect(value).toBe(TEST_DATA.AUTH.PASSWORD);
    }
  });

  test('should select first available option correctly', async () => {
    await helpers.navigateWithChecks('/networks/export');
    await helpers.selectFirstAvailableOption(
      'select, [data-testid="network-selector"]'
    );
  });
});
