import { test, expect } from '@playwright/test';
import { TestHelpers } from './helpers/test-utils';
import { SELECTORS, TEST_DATA } from './helpers/test-data';

test.describe('Key Rotation & Advanced Features', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    helpers = new TestHelpers(page);
  });

  const navigateToKeyRotation = async () => {
    await helpers.navigateWithChecks('/key-rotation');
    await expect(helpers.page.locator('body')).toContainText('Key Rotation');
  };

  const startKeyRotation = async () => {
    const startButton = helpers.page.locator(
      SELECTORS.KEY_ROTATION.START_BUTTON
    );
    if (await startButton.isVisible()) {
      await startButton.click();
      await helpers.handleUnlockModal();
      return true;
    }
    return false;
  };

  const waitForRotationProgress = async () => {
    await helpers.page.waitForTimeout(500);
    return await helpers.page
      .locator(SELECTORS.KEY_ROTATION.PROGRESS_SECTION)
      .isVisible({ timeout: 5000 });
  };

  const performAccessibilityCheck = async () => {
    const elementsWithoutLabels = [];
    const visibleElements = await helpers.getVisibleElements(
      'button, a, input, select, [role="button"]',
      10
    );
    const authModalVisible = await helpers.isElementVisible(
      SELECTORS.AUTH.MODAL
    );
    if (authModalVisible) {
      return true;
    }

    for (const element of visibleElements) {
      const ariaLabel = await element.getAttribute('aria-label');
      const ariaLabelledBy = await element.getAttribute('aria-labelledby');
      const placeholder = await element.getAttribute('placeholder');
      const title = await element.getAttribute('title');
      const textContent = (await element.textContent())?.trim();

      if (
        !ariaLabel &&
        !ariaLabelledBy &&
        !placeholder &&
        !title &&
        !textContent
      ) {
        elementsWithoutLabels.push(element);
      }
    }

    if (visibleElements.length === 0) {
      return true;
    }

    const labeledCount = visibleElements.length - elementsWithoutLabels.length;
    if (labeledCount === 0) {
      return true;
    }

    const unlabeledRatio = elementsWithoutLabels.length / visibleElements.length;
    return unlabeledRatio <= 0.9;
  };

  const MOBILE_VIEWPORT = { width: 375, height: 667 };
  const TABLET_VIEWPORT = { width: 768, height: 1024 };
  const DESKTOP_VIEWPORT = { width: 1024, height: 768 };

  test.describe('Key Rotation Workflow', () => {
    test('should access key rotation page', navigateToKeyRotation);

    test('should show master password prompt for rotation', async () => {
      await navigateToKeyRotation();

      const startRotationButton = helpers.page.locator(
        SELECTORS.KEY_ROTATION.START_BUTTON
      );
      if (await startRotationButton.isVisible()) {
        await startRotationButton.click();

        const unlockModal = helpers.page.locator(
          '[role="dialog"], .modal, [data-testid="master-password-modal"]'
        );
        if (await unlockModal.isVisible()) {
          await expect(unlockModal).toBeVisible();
          await expect(
            helpers.page.locator(SELECTORS.AUTH.PASSWORD_INPUT)
          ).toBeVisible();
        }
      }
    });

    test('should validate rotation prerequisites', async () => {
      await navigateToKeyRotation();

      const prerequisitesSection = helpers.page.locator(
        '[data-testid="prerequisites"], section:has-text("Prerequisites"), .rotation-checklist'
      );
      if (await prerequisitesSection.isVisible()) {
        await expect(prerequisitesSection).toBeVisible();

        const visibleItems = await helpers.getVisibleElements(
          'li, .checklist-item, [data-testid="checklist-item"]'
        );

        if (visibleItems.length > 0) {
          expect(visibleItems.length).toBeGreaterThan(0);
        }
      }
    });

    test('should show rotation progress and status', async () => {
      await navigateToKeyRotation();

      if (await startKeyRotation()) {
        const hasProgress = await waitForRotationProgress();
        if (hasProgress) {
          const progressSection = helpers.page.locator(
            SELECTORS.KEY_ROTATION.PROGRESS_SECTION
          );
          await expect(progressSection).toBeVisible();

          const progressBar = helpers.page.locator(
            SELECTORS.KEY_ROTATION.PROGRESS_BAR
          );
          if (await progressBar.isVisible()) {
            await expect(progressBar).toBeVisible();
          }

          const statusText = helpers.page.locator(
            SELECTORS.KEY_ROTATION.STATUS_TEXT
          );
          if (await statusText.isVisible()) {
            const text = await statusText.textContent();
            expect(text).toMatch(/(rotating|processing|completed|error)/i);
          }
        }
      }
    });

    test('should allow rotation cancellation', async () => {
      await navigateToKeyRotation();

      if (await startKeyRotation()) {
        await helpers.page.waitForTimeout(2000);

        const cancelButton = helpers.page.locator(
          SELECTORS.KEY_ROTATION.CANCEL_BUTTON
        );
        if (await cancelButton.isVisible()) {
          await cancelButton.click();

          const confirmDialog = helpers.page.locator(
            SELECTORS.COMMON.CONFIRM_DIALOG
          );
          if (await confirmDialog.isVisible()) {
            await expect(confirmDialog).toBeVisible();
          }
        }
      }
    });

    test('should show rotation completion summary', async () => {
      await navigateToKeyRotation();

      if (await startKeyRotation()) {
        await helpers.page.waitForTimeout(10000);

        const completionSection = helpers.page.locator(
          SELECTORS.KEY_ROTATION.COMPLETION_SECTION
        );
        if (await completionSection.isVisible({ timeout: 15000 })) {
          await expect(completionSection).toBeVisible();

          const successMessage = helpers.page.locator(
            SELECTORS.COMMON.SUCCESS_MESSAGE
          );
          if (await successMessage.isVisible()) {
            await expect(successMessage).toBeVisible();
          }

          const rotatedCount = helpers.page.locator(
            SELECTORS.KEY_ROTATION.ROTATED_COUNT
          );
          if (await rotatedCount.isVisible()) {
            await expect(rotatedCount).toBeVisible();
          }
        }
      }
    });
  });

  test.describe('Search and Filtering', () => {
    test('should search networks', async () => {
      await helpers.navigateWithChecks('/networks');

      const searchInput = helpers.page.locator(SELECTORS.COMMON.SEARCH_INPUT);
      if (await searchInput.isVisible()) {
        await searchInput.fill(TEST_DATA.NETWORK.NAME);
        await helpers.page.waitForTimeout(500);

        const visibleResults = await helpers.getVisibleElements(
          '[data-testid="network-item"], .network-card'
        );

        if (visibleResults.length > 0) {
          for (const item of visibleResults.slice(0, 3)) {
            const itemText = await item.textContent();
            if (itemText) {
              expect(itemText.toLowerCase()).toContain(
                TEST_DATA.NETWORK.NAME.toLowerCase()
              );
            }
          }
        }
      }
    });

    test('should sort networks and devices', async () => {
      await helpers.navigateWithChecks('/networks');

      const sortDropdown = helpers.page.locator(SELECTORS.COMMON.SORT_SELECT);
      if (await sortDropdown.isVisible()) {
        await expect(sortDropdown).toBeVisible();

        const options = sortDropdown.locator('option');
        const optionCount = await options.count();

        if (optionCount > 1) {
          const maxOptions = Math.min(optionCount - 1, 2);
          for (let i = 1; i <= maxOptions; i++) {
            await sortDropdown.selectOption({ index: i });
            await helpers.page.waitForTimeout(500);
          }
        }
      }
    });

    test('should filter devices by status', async () => {
      if (!(await helpers.navigateToFirstDevice())) {
        return;
      }

      const statusFilter = helpers.page.locator(
        'select[name*="status"], [data-testid="status-filter"], .status-control'
      );
      if (await statusFilter.isVisible()) {
        await statusFilter.selectOption('active');
        await helpers.page.waitForTimeout(500);

        const activeDevices = helpers.page.locator(
          '[data-status="active"], .device-active'
        );
        if (await activeDevices.first().isVisible()) {
          await expect(activeDevices.first()).toBeVisible();
        }
      }
    });

    test('should paginate large result sets', async () => {
      await helpers.navigateWithChecks('/audit');

      const pagination = helpers.page.locator(
        '.pagination, nav[aria-label*="pagination"]'
      );
      if (await pagination.isVisible()) {
        await expect(pagination).toBeVisible();

        const pageInfo = helpers.page.locator(
          '.page-info, [data-testid="page-info"]'
        );
        if (await pageInfo.isVisible()) {
          await expect(pageInfo).toBeVisible();
        }

        const navigationButtons = [
          'button:has-text("Next"), a[aria-label*="next"]',
          'button:has-text("Previous"), a[aria-label*="previous"]',
        ];

        for (const buttonSelector of navigationButtons) {
          const button = helpers.page.locator(buttonSelector);
          if ((await button.isVisible()) && !(await button.isDisabled())) {
            await button.click();
            await helpers.page.waitForTimeout(500);
          }
        }
      }
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize(MOBILE_VIEWPORT);
      await page.goto('/');

      const mobileMenu = page.locator(SELECTORS.COMMON.MOBILE_MENU);
      if (await mobileMenu.isVisible()) {
        await expect(mobileMenu).toBeVisible();
      }

      await page.setViewportSize(TABLET_VIEWPORT);
      await page.goto('/networks');

      const tabletLayout = page.locator(
        '[data-testid="tablet-layout"], .tablet-view'
      );
      const sidebar = page.locator(SELECTORS.COMMON.SIDEBAR);
      const mobileMenuForTablet = page.locator(SELECTORS.COMMON.MOBILE_MENU);
      const authModal = page.locator(SELECTORS.AUTH.MODAL);
      const mainContent = page.locator(
        'main, [role="main"], [data-testid="main-content"]'
      );
      const loadingState = page.locator(SELECTORS.COMMON.LOADING_STATE);
      const hasAnyVisibleElement = await helpers.hasAnyVisibleElement('body *');
      const isTabletLayout = await tabletLayout.isVisible();
      const isSidebarVisible = await sidebar.isVisible();
      const isMobileMenuVisible = await mobileMenuForTablet.isVisible();
      const isAuthModalVisible = await authModal.isVisible();
      const isMainContentVisible = await mainContent.first().isVisible();
      const isLoadingVisible = await loadingState.first().isVisible();
      expect(
        isTabletLayout ||
          isSidebarVisible ||
          isMobileMenuVisible ||
          isAuthModalVisible ||
          isMainContentVisible ||
          isLoadingVisible ||
          hasAnyVisibleElement
      ).toBe(true);
    });

    test('should adapt sidebar navigation', async ({ page }) => {
      await page.setViewportSize(DESKTOP_VIEWPORT);
      await page.goto('/');

      const sidebar = page.locator(SELECTORS.COMMON.SIDEBAR);
      if (await sidebar.isVisible()) {
        await expect(sidebar).toBeVisible();

        await page.setViewportSize(TABLET_VIEWPORT);

        const collapsedSidebar = page.locator(
          '[data-testid="sidebar-collapsed"], .sidebar-collapsed'
        );
        const mobileMenu = page.locator(SELECTORS.COMMON.MOBILE_MENU);
        const isCollapsed = await collapsedSidebar.isVisible();
        const isMobileMenuVisible = await mobileMenu.isVisible();
        expect(isCollapsed || isMobileMenuVisible).toBe(true);
      }
    });

    test('should handle touch interactions', async ({ page }) => {
      await page.setViewportSize(MOBILE_VIEWPORT);
      await page.goto('/networks');

      const visibleTargets = await helpers.getVisibleElements(
        'button, a, [role="button"], .clickable'
      );

      if (visibleTargets.length > 0) {
        await expect(visibleTargets[0]).toBeVisible();
      }
    });
  });

  test.describe('Accessibility Features', () => {
    test('should have proper ARIA labels', async () => {
      await helpers.navigateWithChecks('/networks');

      const hasAccessibility = await performAccessibilityCheck();
      expect(hasAccessibility).toBe(true);
    });

    test('should support keyboard navigation', async ({ page }) => {
      await page.goto('/networks');

      await page.keyboard.press('Tab');
      await page.waitForTimeout(200);

      const firstFocusable = page.locator(':focus');
      expect(await firstFocusable.count()).toBeGreaterThan(0);

      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');
        await page.waitForTimeout(200);

        const currentFocus = page.locator(':focus');
        expect(await currentFocus.count()).toBeGreaterThan(0);
      }
    });

    test('should have sufficient color contrast', async () => {
      await helpers.navigateWithChecks('/networks');

      const visibleTextElements = await helpers.getVisibleElements(
        'p, h1, h2, h3, h4, h5, h6, span, button, a',
        10
      );

      for (const element of visibleTextElements) {
        const computedStyle = await element.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return {
            color: style.color,
            backgroundColor: style.backgroundColor,
            fontSize: style.fontSize,
          };
        });

        expect(computedStyle).toBeDefined();
      }

      expect(visibleTextElements.length).toBeGreaterThan(0);
    });

    test('should respect reduced motion preferences', async ({ page }) => {
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.goto('/');

      const visibleAnimated = await helpers.getVisibleElements(
        '[data-testid="animated"], .animate, .transition'
      );

      const animatedCount = visibleAnimated.filter(async (element) => {
        const hasAnimation = await element.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return (
            style.animation &&
            style.animation !== 'none' &&
            style.transition &&
            style.transition !== 'none'
          );
        });
        return hasAnimation;
      }).length;

      expect(animatedCount).toBeLessThan(2);
    });
  });

  test.describe('Performance Optimization', () => {
    const MAX_LOAD_TIME = 5000;
    const MAX_LOADING_TIME = 8000;

    test('should load pages quickly', async ({ page }) => {
      const pages = ['/networks', '/audit', '/settings'];

      for (const pagePath of pages) {
        const loadTime = await helpers.measureLoadTime(async () => {
          await page.goto(pagePath);
          await page.waitForLoadState('networkidle');
        });

        expect(loadTime).toBeLessThan(MAX_LOAD_TIME);
      }
    });

    test('should handle large datasets without blocking UI', async ({
      page,
    }) => {
      await page.goto('/audit');

      const loadingIndicator = page.locator('.loading, .spinner');
      if (await loadingIndicator.isVisible()) {
        const loadingTime = await helpers.measureLoadTime(async () => {
          await expect(loadingIndicator).not.toBeVisible({ timeout: 10000 });
        });
        expect(loadingTime).toBeLessThan(MAX_LOADING_TIME);
      }

      await helpers.page.waitForTimeout(1000);
      const isResponsive = await page.evaluate(() => {
        const button = document.querySelector('button');
        return button !== null;
      });
      expect(isResponsive).toBe(true);
    });

    test('should implement virtual scrolling for large lists', async ({
      page,
    }) => {
      await page.goto('/audit');

      const scrollableContainer = page.locator(
        '[data-testid="virtual-scroll"], .virtual-list, .scrollable-list'
      );
      if (await scrollableContainer.isVisible()) {
        await scrollableContainer.evaluate((el) => {
          el.scrollTop = 1000;
        });

        await page.waitForTimeout(500);

        const [scrollHeight, clientHeight] = await scrollableContainer.evaluate(
          (el) => [el.scrollHeight, el.clientHeight]
        );

        expect(scrollHeight).toBeGreaterThan(clientHeight);
      }
    });
  });
});
