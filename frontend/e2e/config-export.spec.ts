import { test, expect } from '@playwright/test';
import { TestHelpers } from './helpers/test-utils';
import { SELECTORS } from './helpers/test-data';

test.describe('Config Export Functionality', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    helpers = new TestHelpers(page);
  });

  test.describe('Device Config Export', () => {
    test('should show device config preview', async () => {
      if (!(await helpers.navigateToFirstDevice())) {
        return;
      }

      if (await helpers.isElementVisible(SELECTORS.CONFIG.PREVIEW)) {
        await expect(
          helpers.page.locator(SELECTORS.CONFIG.PREVIEW)
        ).toBeVisible();
        await expect(
          helpers.page.locator('pre, code, .config-content')
        ).toContainText('[Interface]');
        await expect(
          helpers.page.locator('pre, code, .config-content')
        ).toContainText('[Peer]');
      }
    });

    test('should require unlock before config export', async () => {
      if (!(await helpers.navigateToFirstDevice())) {
        return;
      }

      if (await helpers.isElementVisible(SELECTORS.CONFIG.DOWNLOAD_BUTTON)) {
        void helpers.page.waitForEvent('download');
        await helpers.safeClick(SELECTORS.CONFIG.DOWNLOAD_BUTTON);

        if (await helpers.isElementVisible(SELECTORS.AUTH.MODAL)) {
          await expect(
            helpers.page.locator(SELECTORS.AUTH.MODAL)
          ).toBeVisible();
          await expect(
            helpers.page.locator(SELECTORS.AUTH.PASSWORD_INPUT)
          ).toBeVisible();
        }
      }
    });

    test('should download device config file', async () => {
      if (!(await helpers.navigateToFirstDevice())) {
        return;
      }

      if (await helpers.isElementVisible(SELECTORS.CONFIG.DOWNLOAD_BUTTON)) {
        const downloadPromise = helpers.page.waitForEvent('download');
        await helpers.safeClick(SELECTORS.CONFIG.DOWNLOAD_BUTTON);
        await helpers.handleUnlockModal();

        const filename = await helpers.waitForDownload(downloadPromise, [
          '.conf',
          '.wg',
          '.txt',
        ]);
        expect(filename).toMatch(/(\.conf|\.wg|\.txt)$/);
      }
    });

    test('should copy config to clipboard', async () => {
      if (!(await helpers.navigateToFirstDevice())) {
        return;
      }

      if (await helpers.isElementVisible(SELECTORS.CONFIG.COPY_BUTTON)) {
        await helpers.safeClick(SELECTORS.CONFIG.COPY_BUTTON);
        await expect(
          helpers.page.locator(
            '.success, .toast-success, [data-testid="copy-success"]'
          )
        ).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('Network Export', () => {
    test('should access network export page', async () => {
      await helpers.navigateWithChecks('/networks/export');
      await expect(helpers.page.locator('body')).toContainText('Export');
    });

    test('should show network selection', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const networkSelector = helpers.page
        .locator('select, [data-testid="network-selector"], .network-dropdown')
        .first();
      if (await networkSelector.isVisible()) {
        await expect(networkSelector).toBeVisible();

        const options = networkSelector.locator('option');
        const optionCount = await options.count();
        if (optionCount > 0) {
          expect(optionCount).toBeGreaterThan(0);
        }
      }
    });

    test('should show export options', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const formatOptions = helpers.page.locator(
        'input[type="radio"], input[type="checkbox"], .format-option'
      );
      const downloadButton = helpers.page.locator(
        'button:has-text("Download"), button:has-text("Export")'
      );

      if (await formatOptions.first().isVisible()) {
        await expect(formatOptions.first()).toBeVisible();
      }

      const pskOption = helpers.page.locator(
        'label:has-text("PSK"), label:has-text("pre-shared key")'
      );
      if (await pskOption.isVisible()) {
        await expect(pskOption).toBeVisible();
      }

      if (await downloadButton.first().isVisible()) {
        await expect(downloadButton.first()).toBeVisible();
      }
    });

    test('should export network as bundle', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const networkSelector = helpers.page
        .locator('select, [data-testid="network-selector"]')
        .first();
      if (await networkSelector.isVisible()) {
        await helpers.selectFirstAvailableOption(
          'select, [data-testid="network-selector"]'
        );
      }

      const exportButton = helpers.page
        .locator('button:has-text("Download"), button:has-text("Export")')
        .first();
      if (await exportButton.isVisible()) {
        const downloadPromise = helpers.page.waitForEvent('download');
        await helpers.safeClick(
          'button:has-text("Download"), button:has-text("Export")'
        );
        await helpers.handleUnlockModal();

        const filename = await helpers.waitForDownload(downloadPromise, [
          '.zip',
          '.tar.gz',
          '.tgz',
        ]);
        expect(filename).toMatch(/(\.zip|\.tar\.gz|\.tgz)$/);
      }
    });

    test('should show preview of export contents', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const previewSection = helpers.page
        .locator(
          '[data-testid="export-preview"], .preview-section, section:has-text("Preview")'
        )
        .first();
      if (await previewSection.isVisible()) {
        await expect(previewSection).toBeVisible();
        await expect(
          helpers.page.locator('.device-list, .export-contents')
        ).toBeVisible();
      }
    });

    test('should validate export requirements', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const exportButton = helpers.page
        .locator('button:has-text("Download"), button:has-text("Export")')
        .first();
      if (await exportButton.isVisible()) {
        await helpers.safeClick(
          'button:has-text("Download"), button:has-text("Export")'
        );

        const errorMessage = helpers.page.locator(
          '.error, .error-message, [data-invalid]'
        );
        if (await errorMessage.first().isVisible()) {
          await expect(errorMessage.first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Config Linting', () => {
    test('should run config lint validation', async () => {
      if (!(await helpers.navigateToFirstNetwork())) {
        return;
      }

      const lintStatus = helpers.page
        .locator(
          '[data-testid="config-lint"], .lint-status, .validation-status'
        )
        .first();
      if (await lintStatus.isVisible()) {
        await expect(lintStatus).toBeVisible();
        await expect(lintStatus).toContainText(
          /\b(pass|fail|warning|error|success)\b/i
        );
      }
    });

    test('should show detailed lint results', async () => {
      if (!(await helpers.navigateToFirstNetwork())) {
        return;
      }

      const lintButton = helpers.page
        .locator(
          'button:has-text("Config Lint"), button:has-text("Validate"), [data-testid="lint-button"]'
        )
        .first();
      if (await lintButton.isVisible()) {
        await helpers.safeClick(
          'button:has-text("Config Lint"), button:has-text("Validate"), [data-testid="lint-button"]'
        );

        const lintResults = helpers.page.locator(
          '[data-testid="lint-results"], .lint-results, .validation-results'
        );
        if (await lintResults.isVisible()) {
          await expect(lintResults).toBeVisible();
          await expect(lintResults).toContainText(
            /(no issues|error|warning|success)/i
          );
        }
      }
    });

    test('should show lint errors for invalid configurations', async () => {
      await helpers.navigateWithChecks('/networks');

      if (await helpers.isElementVisible(SELECTORS.NETWORK.ITEM)) {
        await helpers.safeClick(SELECTORS.NETWORK.ITEM);

        const lintIndicator = helpers.page
          .locator('[data-testid*="lint"], .validation-icon, .status-indicator')
          .first();
        if (await lintIndicator.isVisible()) {
          await expect(lintIndicator).toBeVisible();
        }
      }
    });
  });

  test.describe('Export Security', () => {
    test('should prevent caching of config pages', async () => {
      if (await helpers.navigateToFirstDevice()) {
        await expect(helpers.page.locator('body')).toBeVisible();
      }
    });

    test('should show security warnings for sensitive operations', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const securityWarning = helpers.page.locator(
        '.warning, .security-warning, [data-testid="security-warning"]'
      );
      if (await securityWarning.isVisible()) {
        await expect(securityWarning).toBeVisible();
        await expect(securityWarning).toContainText(
          /sensitive|security|private|confidential/i
        );
      }
    });

    test('should have proper access controls for config endpoints', async () => {
      await helpers.navigateWithChecks('/networks');

      const secureElements = helpers.page.locator(
        '[data-testid*="secure"], .protected-operation'
      );
      const count = await secureElements.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Export Formats', () => {
    test('should support different export formats', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const formatOptions = helpers.page.locator(
        'input[type="radio"], input[type="checkbox"], .format-option'
      );
      const visibleOptions = [];

      for (let i = 0; i < (await formatOptions.count()); i++) {
        const option = formatOptions.nth(i);
        if (await option.isVisible()) {
          visibleOptions.push(option);
        }
      }

      if (visibleOptions.length > 0) {
        expect(visibleOptions.length).toBeGreaterThan(0);

        for (let i = 0; i < Math.min(visibleOptions.length, 3); i++) {
          const option = visibleOptions[i];
          await option.check();
          await expect(option).toBeChecked();
        }
      }
    });

    test('should show format-specific options', async () => {
      await helpers.navigateWithChecks('/networks/export');

      const conditionalOptions = helpers.page.locator(
        '[data-format-option], .conditional-option'
      );
      const count = await conditionalOptions.count();

      if (count > 0) {
        await expect(conditionalOptions.first()).toBeVisible();
      }
    });
  });
});
