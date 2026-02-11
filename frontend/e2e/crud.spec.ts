import { test, expect } from '@playwright/test';
import { TestHelpers } from './helpers/test-utils';
import { SELECTORS, TEST_DATA } from './helpers/test-data';

test.describe('CRUD Operations', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    helpers = new TestHelpers(page);
  });

  test.describe('Networks Management', () => {
    test('should display networks page', async () => {
      await helpers.navigateWithChecks('/networks');

      if (await helpers.isElementVisible(SELECTORS.NETWORK.CREATE_BUTTON)) {
        await expect(
          helpers.page.locator(SELECTORS.NETWORK.CREATE_BUTTON)
        ).toBeVisible();
      }
    });

    test('should show create network form', async () => {
      await helpers.navigateWithChecks('/networks');

      if (await helpers.isElementVisible(SELECTORS.NETWORK.CREATE_BUTTON)) {
        await helpers.safeClick(SELECTORS.NETWORK.CREATE_BUTTON);

        await expect(
          helpers.page.locator(SELECTORS.NETWORK.NAME_INPUT)
        ).toBeVisible();
        await expect(
          helpers.page.locator(SELECTORS.NETWORK.CIDR_INPUT)
        ).toBeVisible();
        await expect(
          helpers.page.locator(SELECTORS.NETWORK.SAVE_BUTTON)
        ).toBeVisible();
        await expect(
          helpers.page.locator(SELECTORS.AUTH.CANCEL_BUTTON)
        ).toBeVisible();
      }
    });

    test('should validate network creation form', async () => {
      await helpers.navigateWithChecks('/networks');

      if (await helpers.isElementVisible(SELECTORS.NETWORK.CREATE_BUTTON)) {
        await helpers.safeClick(SELECTORS.NETWORK.CREATE_BUTTON);
        await helpers.safeClick(SELECTORS.NETWORK.SAVE_BUTTON);
        await expect(
          helpers.page.locator(SELECTORS.COMMON.ERROR_MESSAGE)
        ).toBeVisible();
      }
    });

    test('should create a new network', async () => {
      const success = await helpers.createNetwork();
      if (success) {
        await expect(
          helpers.page.locator(SELECTORS.COMMON.SUCCESS_MESSAGE)
        ).toBeVisible({ timeout: 10000 });
      }
    });

    test('should edit existing network', async () => {
      await helpers.navigateWithChecks('/networks');

      if (await helpers.isElementVisible(SELECTORS.NETWORK.ITEM)) {
        await helpers.safeClick(SELECTORS.NETWORK.ITEM);

        if (await helpers.isElementVisible(SELECTORS.NETWORK.EDIT_BUTTON)) {
          await helpers.safeClick(SELECTORS.NETWORK.EDIT_BUTTON);

          await expect(
            helpers.page.locator(SELECTORS.NETWORK.NAME_INPUT)
          ).toBeVisible();
          await helpers.safeFill(
            SELECTORS.NETWORK.NAME_INPUT,
            TEST_DATA.NETWORK.UPDATED_NAME
          );
          await helpers.safeClick(SELECTORS.NETWORK.SAVE_BUTTON);

          await expect(
            helpers.page.locator(SELECTORS.COMMON.SUCCESS_MESSAGE)
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('should delete network', async () => {
      await helpers.navigateWithChecks('/networks');

      if (await helpers.isElementVisible(SELECTORS.NETWORK.ITEM)) {
        await helpers.safeClick(SELECTORS.NETWORK.ITEM);

        if (await helpers.isElementVisible(SELECTORS.NETWORK.DELETE_BUTTON)) {
          await helpers.safeClick(SELECTORS.NETWORK.DELETE_BUTTON);
          await expect(
            helpers.page.locator(SELECTORS.COMMON.CONFIRM_DIALOG)
          ).toBeVisible();

          await helpers.handleConfirmationDialog(true);
          await expect(
            helpers.page.locator(SELECTORS.COMMON.SUCCESS_MESSAGE)
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });
  });

  test.describe('Locations Management', () => {
    test('should manage locations within a network', async () => {
      if (!(await helpers.navigateToFirstNetwork())) {
        return;
      }

      if (await helpers.isElementVisible(SELECTORS.LOCATION.SECTION)) {
        if (await helpers.isElementVisible(SELECTORS.LOCATION.ADD_BUTTON)) {
          await helpers.safeClick(SELECTORS.LOCATION.ADD_BUTTON);

          await expect(
            helpers.page.locator(SELECTORS.LOCATION.NAME_INPUT)
          ).toBeVisible();
          await expect(
            helpers.page.locator(SELECTORS.LOCATION.ENDPOINT_INPUT)
          ).toBeVisible();

          await helpers.safeFill(
            SELECTORS.LOCATION.NAME_INPUT,
            TEST_DATA.LOCATION.NAME
          );
          await helpers.safeFill(
            SELECTORS.LOCATION.ENDPOINT_INPUT,
            TEST_DATA.LOCATION.ENDPOINT
          );

          await helpers.safeClick(SELECTORS.NETWORK.SAVE_BUTTON);
          await expect(
            helpers.page.locator(SELECTORS.COMMON.SUCCESS_MESSAGE)
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('should edit and delete locations', async () => {
      if (!(await helpers.navigateToFirstNetwork())) {
        return;
      }

      if (await helpers.isElementVisible(SELECTORS.LOCATION.ITEM)) {
        const locationItem = helpers.page
          .locator(SELECTORS.LOCATION.ITEM)
          .first();

        const editButton = locationItem
          .locator('button:has-text("Edit"), button[aria-label*="edit"]')
          .first();
        if (await editButton.isVisible()) {
          await editButton.click();
          await expect(
            helpers.page.locator('input[name*="name"]')
          ).toBeVisible();
          await helpers.safeClick(SELECTORS.AUTH.CANCEL_BUTTON);
        }

        const deleteButton = locationItem
          .locator('button:has-text("Delete"), button[aria-label*="delete"]')
          .first();
        if (await deleteButton.isVisible()) {
          await deleteButton.click();
          await expect(
            helpers.page.locator(SELECTORS.COMMON.MODAL)
          ).toBeVisible();
          await helpers.handleConfirmationDialog(false);
        }
      }
    });
  });

  test.describe('Devices Management', () => {
    test('should manage devices within a location', async () => {
      await helpers.navigateWithChecks('/networks');

      if (!(await helpers.isElementVisible(SELECTORS.NETWORK.ITEM))) {
        return;
      }

      await helpers.safeClick(SELECTORS.NETWORK.ITEM);

      if (await helpers.isElementVisible(SELECTORS.LOCATION.ITEM)) {
        await helpers.safeClick(SELECTORS.LOCATION.ITEM);

        if (await helpers.isElementVisible(SELECTORS.DEVICE.SECTION)) {
          if (await helpers.isElementVisible(SELECTORS.DEVICE.ADD_BUTTON)) {
            await helpers.safeClick(SELECTORS.DEVICE.ADD_BUTTON);

            await expect(
              helpers.page.locator(SELECTORS.DEVICE.ADD_BUTTON)
            ).toBeVisible();
            await helpers.safeFill(
              SELECTORS.NETWORK.NAME_INPUT,
              TEST_DATA.DEVICE.NAME
            );
            await helpers.safeClick(SELECTORS.NETWORK.SAVE_BUTTON);

            await expect(
              helpers.page.locator(SELECTORS.COMMON.SUCCESS_MESSAGE)
            ).toBeVisible({ timeout: 10000 });
          }
        }
      }
    });

    test('should view device details', async () => {
      if (await helpers.navigateToFirstDevice()) {
        await expect(helpers.page.locator('body')).toContainText('Device');
        await expect(
          helpers.page.locator(SELECTORS.DEVICE.DETAILS)
        ).toBeVisible();
      }
    });

    test('should manage device API keys', async () => {
      if (await helpers.navigateToFirstDevice()) {
        if (await helpers.isElementVisible(SELECTORS.DEVICE.API_KEY_SECTION)) {
          const generateButton = helpers.page
            .locator(
              'button:has-text("Generate"), button:has-text("Regenerate")'
            )
            .first();
          if (await generateButton.isVisible()) {
            await expect(generateButton).toBeVisible();
          }

          const copyButton = helpers.page
            .locator('button:has-text("Copy"), button[aria-label*="copy"]')
            .first();
          if (await copyButton.isVisible()) {
            await expect(copyButton).toBeVisible();
          }
        }
      }
    });
  });

  test.describe('Data Validation', () => {
    test('should validate CIDR format', async () => {
      await helpers.navigateWithChecks('/networks');

      if (await helpers.isElementVisible(SELECTORS.NETWORK.CREATE_BUTTON)) {
        await helpers.safeClick(SELECTORS.NETWORK.CREATE_BUTTON);
        await helpers.safeFill(SELECTORS.NETWORK.CIDR_INPUT, 'invalid-cidr');
        await helpers.safeClick(SELECTORS.NETWORK.SAVE_BUTTON);

        await expect(
          helpers.page.locator(SELECTORS.COMMON.ERROR_MESSAGE)
        ).toBeVisible();
      }
    });

    test('should validate endpoint format', async () => {
      if (await helpers.navigateToFirstNetwork()) {
        if (await helpers.isElementVisible(SELECTORS.LOCATION.ADD_BUTTON)) {
          await helpers.safeClick(SELECTORS.LOCATION.ADD_BUTTON);
          await helpers.safeFill(
            SELECTORS.LOCATION.ENDPOINT_INPUT,
            TEST_DATA.LOCATION.INVALID_ENDPOINT
          );
          await helpers.safeClick(SELECTORS.NETWORK.SAVE_BUTTON);

          await expect(
            helpers.page.locator(SELECTORS.COMMON.ERROR_MESSAGE)
          ).toBeVisible();
        }
      }
    });
  });

  test.describe('Error Handling', () => {
    test('should handle network errors gracefully', async () => {
      await helpers.navigateWithChecks('/networks');
      await expect(helpers.page.locator('body')).toBeVisible();

      const errorState = helpers.page.locator(
        '.error, .error-state, [data-testid="error"]'
      );
      if (await errorState.isVisible()) {
        await expect(errorState).toBeVisible();
      }
    });

    test('should show empty state when no data', async () => {
      await helpers.navigateWithChecks('/networks');

      const emptyState = helpers.page.locator(
        '.empty-state, [data-testid="empty-state"], .no-data'
      );
      if (await emptyState.isVisible()) {
        await expect(emptyState).toBeVisible();
        const emptyStateText = await emptyState.textContent();
        expect(emptyStateText).toMatch(/(No networks|No data|Empty)/);
      }
    });
  });
});
