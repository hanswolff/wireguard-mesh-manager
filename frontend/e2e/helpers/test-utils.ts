import { Page, Locator, expect, Download } from '@playwright/test';
import { SELECTORS, TEST_DATA } from './test-data';

const DEFAULT_TIMEOUT = 10000;
const SHORT_TIMEOUT = 2000;
const MAX_VISIBLE_ITEMS = 5;
const NETWORK_IDLE_TIMEOUT = 30000;

export class TestHelpers {
  constructor(public page: Page) {}

  async waitForElement(
    selector: string,
    timeout = DEFAULT_TIMEOUT
  ): Promise<Locator> {
    const element = this.page.locator(selector).first();
    await expect(element).toBeVisible({ timeout });
    return element;
  }

  async isElementVisible(
    selector: string,
    timeout = SHORT_TIMEOUT
  ): Promise<boolean> {
    try {
      await expect(this.page.locator(selector).first()).toBeVisible({
        timeout,
      });
      return true;
    } catch {
      return false;
    }
  }

  async safeClick(selector: string): Promise<boolean> {
    const element = this.page.locator(selector).first();
    if (await element.isVisible()) {
      await element.click();
      return true;
    }
    return false;
  }

  async safeFill(selector: string, value: string): Promise<boolean> {
    const element = this.page.locator(selector).first();
    if (await element.isVisible()) {
      await element.fill(value);
      return true;
    }
    return false;
  }

  async selectFirstAvailableOption(selector: string): Promise<boolean> {
    const element = this.page.locator(selector).first();
    if (await element.isVisible()) {
      const options = element.locator('option');
      const optionCount = await options.count();
      if (optionCount > 1) {
        await element.selectOption({ index: 1 });
        return true;
      }
    }
    return false;
  }

  async navigateWithChecks(path: string): Promise<void> {
    await this.page.goto(path);
    await expect(this.page.locator('body')).toBeVisible();
  }

  async waitForNetwork(): Promise<void> {
    await this.page.waitForLoadState('networkidle', {
      timeout: NETWORK_IDLE_TIMEOUT,
    });
  }

  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded');
    await this.page.waitForLoadState('networkidle');
  }

  async handleUnlockModal(): Promise<boolean> {
    if (await this.isElementVisible(SELECTORS.AUTH.MODAL)) {
      const filled = await this.safeFill(
        SELECTORS.AUTH.PASSWORD_INPUT,
        TEST_DATA.AUTH.PASSWORD
      );
      if (filled) {
        await this.safeClick(SELECTORS.AUTH.SUBMIT_BUTTON);
        await this.waitForNetwork();
        return true;
      }
    }
    return false;
  }

  async handleConfirmationDialog(shouldConfirm = true): Promise<boolean> {
    if (await this.isElementVisible(SELECTORS.COMMON.CONFIRM_DIALOG)) {
      const confirmButton = shouldConfirm
        ? 'button:has-text("Delete"), button:has-text("Confirm"), button.danger'
        : 'button:has-text("Cancel")';
      return await this.safeClick(confirmButton);
    }
    return false;
  }

  async createNetwork(name?: string, cidr?: string): Promise<boolean> {
    const networkName = name || TEST_DATA.NETWORK.NAME;
    const networkCidr = cidr || TEST_DATA.NETWORK.CIDR;

    await this.navigateWithChecks('/networks');

    if (!(await this.isElementVisible(SELECTORS.NETWORK.CREATE_BUTTON))) {
      return false;
    }

    await this.safeClick(SELECTORS.NETWORK.CREATE_BUTTON);
    await this.safeFill(SELECTORS.NETWORK.NAME_INPUT, networkName);
    await this.safeFill(SELECTORS.NETWORK.CIDR_INPUT, networkCidr);
    await this.safeClick(SELECTORS.NETWORK.SAVE_BUTTON);

    return await this.isElementVisible(SELECTORS.COMMON.SUCCESS_MESSAGE, 5000);
  }

  async navigateToFirstNetwork(): Promise<boolean> {
    await this.navigateWithChecks('/networks');

    if (!(await this.isElementVisible(SELECTORS.NETWORK.ITEM))) {
      return false;
    }

    return await this.safeClick(SELECTORS.NETWORK.ITEM);
  }

  async navigateToFirstDevice(): Promise<boolean> {
    if (!(await this.navigateToFirstNetwork())) {
      return false;
    }

    const deviceLink = this.page.locator('a[href*="devices"]').first();
    if (!(await deviceLink.isVisible())) {
      return false;
    }

    await deviceLink.click();

    if (await this.isElementVisible(SELECTORS.DEVICE.ITEM)) {
      return await this.safeClick(SELECTORS.DEVICE.ITEM);
    }

    return false;
  }

  async waitForDownload(
    downloadPromise: Promise<Download>,
    expectedExtensions = ['.conf', '.wg', '.txt', '.zip', '.tar.gz', '.tgz']
  ): Promise<string> {
    const download = await downloadPromise;
    const filename = download.suggestedFilename();

    const hasValidExtension = expectedExtensions.some((ext) =>
      filename.endsWith(ext)
    );
    if (!hasValidExtension) {
      throw new Error(`Invalid download filename: ${filename}`);
    }

    return filename;
  }

  async getVisibleElements(
    selector: string,
    maxItems = MAX_VISIBLE_ITEMS
  ): Promise<Locator[]> {
    const elements = this.page.locator(selector);
    const visibleElements: Locator[] = [];
    const count = await elements.count();

    for (let i = 0; i < Math.min(count, maxItems); i++) {
      const element = elements.nth(i);
      if (await element.isVisible()) {
        visibleElements.push(element);
      }
    }

    return visibleElements;
  }

  async waitForTextContent(selector: string): Promise<string[]> {
    const elements = await this.getVisibleElements(selector);
    const contents: string[] = [];

    for (const element of elements) {
      const text = await element.textContent();
      if (text) {
        contents.push(text);
      }
    }

    return contents;
  }

  async hasAnyVisibleElement(selector: string): Promise<boolean> {
    return (await this.getVisibleElements(selector, 1)).length > 0;
  }

  async measureLoadTime(action: () => Promise<void>): Promise<number> {
    const startTime = Date.now();
    await action();
    return Date.now() - startTime;
  }
}
