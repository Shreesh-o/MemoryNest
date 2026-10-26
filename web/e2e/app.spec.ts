import { test, expect, Page, BrowserContext } from '@playwright/test';

const EMAIL = `e2e_${Date.now()}@example.com`;
const PASSWORD = 'demo1234';
const USERNAME = `e2e_${Date.now()}`;

const consoleErrors: string[] = [];
const pageErrors: string[] = [];

function attachErrorCollectors(p: Page) {
  p.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(`${msg.type()}: ${msg.text()}`);
    }
  });
  p.on('pageerror', error => {
    pageErrors.push(error.message);
  });
}

test.describe('MemoryNest E2E Tests', () => {
  let context: BrowserContext;
  let page: Page;
  const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000';
  const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8000';

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ baseURL });
    page = await context.newPage();
    attachErrorCollectors(page);
  });

  test.afterAll(async () => {
    await context.close();
  });

  test.beforeEach(async () => {
    await context.clearCookies();
  });

  test.describe('T1: Logged out redirects', () => {
    test('T1: /dashboard redirects to /login', async () => {
      await page.goto('/dashboard');
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
      await expect(page.getByRole('heading', { name: /memorynest/i }).or(page.getByText('MemoryNest').first())).toBeVisible({ timeout: 5000 });
      await page.screenshot({ path: 'e2e/screenshots/T1-dashboard-redirect.png', fullPage: true });
    });

    test('T1: /documents redirects to /login', async () => {
      await page.goto('/documents');
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
      await expect(page.getByRole('heading', { name: /memorynest/i }).or(page.getByText('MemoryNest').first())).toBeVisible({ timeout: 5000 });
      await page.screenshot({ path: 'e2e/screenshots/T1-documents-redirect.png', fullPage: true });
    });

    test('T1: /upload redirects to /login', async () => {
      await page.goto('/upload');
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
      await expect(page.getByRole('heading', { name: /memorynest/i }).or(page.getByText('MemoryNest').first())).toBeVisible({ timeout: 5000 });
      await page.screenshot({ path: 'e2e/screenshots/T1-upload-redirect.png', fullPage: true });
    });
  });

  test.describe('T2: Register and login', () => {
    test('T2: Register new user and login', async () => {
      await page.goto('/register');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/email/i).fill(EMAIL);
      await page.getByLabel(/password/i).first().fill(PASSWORD);
      await page.getByLabel(/confirm password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /create account|register/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
      await page.screenshot({ path: 'e2e/screenshots/T2-register-success.png', fullPage: true });
      await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /documents/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /upload/i })).toBeVisible();
      const cookies = await context.cookies();
      expect(cookies.find(c => c.name === 'mn_session')).toBeTruthy();
      await page.screenshot({ path: 'e2e/screenshots/T2-dashboard.png', fullPage: true });
    });

    test('T3: Reload /dashboard stays on /dashboard', async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
      await page.reload();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
      await page.screenshot({ path: 'e2e/screenshots/T3-reload.png', fullPage: true });
    });
  });

  test.describe('T4: Sidebar navigation', () => {
    test.beforeEach(async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    });

    test('T4: Sidebar shows Dashboard, Documents, Upload and Soon badges', async () => {
      await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /documents/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /upload/i })).toBeVisible();
      await expect(page.locator('text=Soon').first()).toBeVisible();
      await expect(page.getByText('Chat')).toBeVisible();
      await expect(page.getByText('Summaries')).toBeVisible();
      await expect(page.getByText('Reminders')).toBeVisible();
      await page.screenshot({ path: 'e2e/screenshots/T4-sidebar.png', fullPage: true });
    });

    test('T4: Soon items do not navigate', async () => {
      await page.getByText('Chat', { exact: true }).click();
      await expect(page).toHaveURL(/\/dashboard/);
      await page.getByText('Summaries', { exact: true }).click();
      await expect(page).toHaveURL(/\/dashboard/);
      await page.getByText('Reminders', { exact: true }).click();
      await expect(page).toHaveURL(/\/dashboard/);
    });
  });

  test.describe('T5: Logout', () => {
    test('T5: Logout redirects to /login and /dashboard redirects to /login', async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
      await page.locator('button:has-text("Log out"), button:has-text("Logout"), button[aria-label*="user"], button:has([aria-label="user"])').first().click().catch(async () => {
        await page.locator('button:has(svg.lucide-user), [aria-label*="account"], [aria-label*="profile"]').first().click();
      });
      await page.getByRole('menuitem', { name: /logout|log out/i }).click().catch(async () => {
        await page.getByRole('button', { name: /logout|log out/i }).click();
      });
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
      await page.screenshot({ path: 'e2e/screenshots/T5-logout.png', fullPage: true });
      await page.goto('/dashboard');
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
      await page.screenshot({ path: 'e2e/screenshots/T5-dashboard-after-logout.png', fullPage: true });
    });
  });

  test.describe('T6: Login with wrong/right password', () => {
    test('T6: Wrong password shows error', async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/login/);
      const errorMsg = await page.locator('.text-destructive, .text-red, [role="alert"], .text-red-500, .text-red-600, [class*="error"]').first().textContent();
      expect(errorMsg && errorMsg.length > 0).toBeTruthy();
      await page.screenshot({ path: 'e2e/screenshots/T6-wrong-password.png', fullPage: true });
    });

    test('T6: Right password logs in', async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
      await page.screenshot({ path: 'e2e/screenshots/T6-correct-password.png', fullPage: true });
    });
  });

  test.describe('T7: Dead cookie handling', () => {
    test('T7: Invalid cookie redirects to login without redirect loop', async () => {
      const deadContext = await page.context().browser()!.newContext({ baseURL });
      const deadPage = await deadContext.newPage();
      await deadContext.addCookies([{ name: 'mn_session', value: 'garbage', domain: '127.0.0.1', path: '/' }]);
      let navCount = 0;
      deadPage.on('framenavigated', () => navCount++);
      await deadPage.goto('/dashboard');
      await expect(deadPage).toHaveURL(/\/login/, { timeout: 15000 });
      expect(navCount).toBeLessThan(6);
      await expect(deadPage.getByRole('heading', { name: /memorynest/i }).or(deadPage.getByText('MemoryNest').first())).toBeVisible({ timeout: 5000 });
      await page.screenshot({ path: 'e2e/screenshots/T7-dead-cookie.png', fullPage: true });
      await deadPage.close();
    });
  });

  test.describe('T8: API unreachable', () => {
    test.beforeEach(async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    });

    test('T8: API unreachable shows error with Retry button', async () => {
      await page.route('**/api/auth/me', route => route.abort());
      await page.reload();
      const errorText = await page.locator('text=/can.t reach|can.t connect|unavailable|offline/i').first().textContent({ timeout: 10000 });
      expect(errorText).toBeTruthy();
      const retryButton = page.getByRole('button', { name: /retry/i });
      await expect(retryButton).toBeVisible({ timeout: 5000 });
      const skeleton = page.locator('.animate-pulse, .skeleton, [data-testid="skeleton"]');
      await expect(skeleton).not.toBeVisible({ timeout: 5000 });
      await page.screenshot({ path: 'e2e/screenshots/T8-api-unreachable.png', fullPage: true });
      await page.unroute('**/api/auth/me');
    });
  });

  test.describe('T9: Documents flow', () => {
    test.beforeEach(async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    });

    test('T9: Upload document, preview, delete', async () => {
      const testContent = `Test document for E2E ${Date.now()}. Meeting scheduled for 2026-10-25.`;
      const files = [{ name: 'e2e-note.txt', mimeType: 'text/plain', buffer: Buffer.from(testContent) }];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const response = await page.request.post(`${apiURL}/api/documents/upload`, { multipart: { files: files as any } });
      const responseJson = await response.json();
      expect(responseJson[0].status).toBe('ready');
      expect(responseJson[0].doc_id).toBeTruthy();
      await page.goto('/documents');
      await expect(page.locator('text=e2e-note.txt')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Ready').first()).toBeVisible();
      await page.getByRole('button', { name: /preview/i }).first().click();
      await expect(page.locator('text=Text Preview')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Test document for E2E')).toBeVisible({ timeout: 5000 });
      await page.keyboard.press('Escape');
      await page.getByRole('button', { name: /delete/i }).first().click();
      await page.getByRole('button', { name: /delete|confirm/i }).click();
      await expect(page.locator('text=e2e-note.txt')).not.toBeVisible({ timeout: 5000 });
      await page.reload();
      await expect(page.locator('text=e2e-note.txt')).not.toBeVisible({ timeout: 5000 });
      await page.screenshot({ path: 'e2e/screenshots/T9-documents-flow.png', fullPage: true });
    });

    test('T9: Empty account shows empty state', async () => {
      await page.goto('/register');
      await page.getByLabel(/username/i).fill(`e2e_fresh_${Date.now()}`);
      await page.getByLabel(/email/i).fill(`fresh_${Date.now()}@example.com`);
      await page.getByLabel(/password/i).first().fill('demo1234');
      await page.getByLabel(/confirm password/i).fill('demo1234');
      await page.getByRole('button', { name: /create account|register/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
      await page.getByRole('link', { name: /documents/i }).click();
      await expect(page.locator('text=No documents yet')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Upload your first document')).toBeVisible();
      await page.screenshot({ path: 'e2e/screenshots/T9-empty-state.png', fullPage: true });
    });
  });

  test.describe('T10: Upload page', () => {
    test.beforeEach(async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    });

    test('T10: Upload page accepts TXT and rejects invalid file', async () => {
      await page.goto('/upload');
      const isPlaceholder = await page.locator('text=/coming soon|placeholder|not implemented/i').isVisible().catch(() => false);
      if (isPlaceholder) {
        await page.screenshot({ path: 'e2e/screenshots/T10-placeholder.png', fullPage: true });
        throw new Error('upload page is a placeholder');
      }
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles([
        { name: 'test.txt', mimeType: 'text/plain', buffer: Buffer.from('Test text file for upload') },
        { name: 'fake.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 fake pdf content') },
      ]);
      await page.getByRole('button', { name: /upload/i }).click();
      await page.waitForSelector('text=ready, text=rejected', { timeout: 15000 });
      const results = await page.locator('text=ready, text=rejected').allTextContents();
      const hasReady = results.some(r => r.includes('ready'));
      const hasRejected = results.some(r => r.includes('rejected'));
      expect(hasReady).toBeTruthy();
      expect(hasRejected).toBeTruthy();
      await page.screenshot({ path: 'e2e/screenshots/T10-upload-results.png', fullPage: true });
    });
  });

  test.describe('T11: Theme toggle', () => {
    test.beforeEach(async () => {
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    });

    test('T11: Theme toggle persists after reload', async () => {
      const themeToggle = page.getByRole('button', { name: /theme|dark|light/i }).first();
      await themeToggle.click();
      await expect(page.locator('html')).toHaveClass(/dark/);
      await page.screenshot({ path: 'e2e/screenshots/T11-dark-mode.png', fullPage: true });
      await page.reload();
      await expect(page.locator('html')).toHaveClass(/dark/);
      await page.screenshot({ path: 'e2e/screenshots/T11-dark-persisted.png', fullPage: true });
    });
  });

  test.describe('T12: Mobile viewport', () => {
    test('T12: Mobile view shows menu button and sheet navigation', async () => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/login');
      await page.getByLabel(/username/i).fill(USERNAME);
      await page.getByLabel(/password/i).fill(PASSWORD);
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
      const sidebar = page.locator('aside, nav[aria-label="sidebar"], [data-testid="sidebar"]');
      await expect(sidebar).not.toBeVisible({ timeout: 5000 });
      const menuButton = page.locator('button[aria-label*="menu"], button:has(svg.lucide-menu), button:has-text("Menu")').first();
      await expect(menuButton).toBeVisible({ timeout: 5000 });
      await menuButton.click();
      const sheet = page.locator('[role="dialog"], [data-testid="sheet"], .sheet-content');
      await expect(sheet).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Dashboard')).toBeVisible();
      await expect(page.locator('text=Documents')).toBeVisible();
      await expect(page.locator('text=Upload')).toBeVisible();
      await page.screenshot({ path: 'e2e/screenshots/T12-mobile.png', fullPage: true });
    });
  });

  test.describe('T13: Error and hydration counts', () => {
    test('T13: Report console errors and hydration warnings', async () => {
      console.log('=== Console Errors ===');
      consoleErrors.forEach(err => console.log(`  - ${err}`));
      console.log(`Total console errors: ${consoleErrors.length}`);
      console.log('=== Page Errors ===');
      pageErrors.forEach(err => console.log(`  - ${err}`));
      console.log(`Total page errors: ${pageErrors.length}`);
      console.log('=== Hydration Warnings ===');
      const hydrationWarnings = consoleErrors.filter(e => e.toLowerCase().includes('hydration') || e.toLowerCase().includes('mismatch'));
      hydrationWarnings.forEach(w => console.log(`  - ${w}`));
      console.log(`Total hydration warnings: ${hydrationWarnings.length}`);
      expect(true).toBeTruthy();
    });
  });
});
