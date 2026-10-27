import { test, expect } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000';
const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8000';

test.describe('Profile & Account Management', () => {
  test('Complete flow: Profile dropdown, update profile, change password, and deactivate account', async ({ page }) => {
    const timestamp = Date.now();
    const initialUsername = `user_${timestamp}`;
    const initialEmail = `user_${timestamp}@example.com`;
    const initialPassword = 'InitialPassword123!';

    // 1. Register test user via API
    const regRes = await fetch(`${apiURL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: initialUsername,
        email: initialEmail,
        password: initialPassword,
      }),
    });
    expect(regRes.status).toBe(201);

    // 2. Login via API and set cookie
    const loginRes = await fetch(`${apiURL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: initialUsername,
        password: initialPassword,
      }),
    });
    expect(loginRes.status).toBe(200);
    const cookieHeader = loginRes.headers.get('set-cookie');
    const match = cookieHeader?.match(/mn_session=([^;]+)/);
    expect(match).toBeTruthy();
    const sessionToken = match![1];

    await page.context().addCookies([{
      name: 'mn_session',
      value: sessionToken,
      domain: '127.0.0.1',
      path: '/',
    }]);

    // 3. Visit Dashboard
    await page.goto(`${baseURL}/dashboard`);
    await page.waitForLoadState('networkidle');

    // 4. Click profile avatar in header - ensure NO CRASH
    const avatar = page.locator('header button').last();
    await expect(avatar).toBeVisible();
    await avatar.click();

    // Check dropdown menu appears with user details and "Profile & Settings" link
    const dropdown = page.locator('[data-slot="dropdown-menu-content"]');
    await expect(dropdown).toBeVisible();
    await expect(dropdown).toContainText(initialUsername);
    await expect(page.getByText('Profile & Settings')).toBeVisible();

    // 5. Click "Profile & Settings"
    await page.getByText('Profile & Settings').click();
    await page.waitForURL('**/profile');
    await expect(page).toHaveURL(/\/profile/);
    await expect(page.getByRole('heading', { name: initialUsername })).toBeVisible();

    // Take screenshot of Profile page
    await page.screenshot({ path: 'e2e/screenshots/profile-page-initial.png' });

    // 6. Test updating name and email
    const updatedUsername = `renamed_${timestamp}`;
    const updatedEmail = `renamed_${timestamp}@example.com`;

    const usernameInput = page.locator('input#username');
    const emailInput = page.locator('input#email');

    await usernameInput.fill(updatedUsername);
    await emailInput.fill(updatedEmail);
    await page.getByRole('button', { name: /save changes/i }).click();

    // Check for success toast
    await expect(page.getByText(/profile updated successfully/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('heading', { name: updatedUsername })).toBeVisible();
    await expect(page.getByText(updatedEmail)).toBeVisible();

    // 7. Test changing password
    const newPassword = 'NewSecretPassword456!';
    await page.locator('input#current-password').fill(initialPassword);
    await page.locator('input#new-password').fill(newPassword);
    await page.locator('input#confirm-password').fill(newPassword);
    await page.getByRole('button', { name: /update password/i }).click();

    await expect(page.getByText(/password changed successfully/i)).toBeVisible({ timeout: 5000 });

    // Take screenshot of updated profile
    await page.screenshot({ path: 'e2e/screenshots/profile-page-updated.png' });

    // 8. Test Account Deactivation
    const deactivateBtn = page.getByRole('button', { name: /deactivate account/i }).first();
    await deactivateBtn.click();

    // Dialog should open
    const dialog = page.locator('[data-slot="dialog-content"]');
    await expect(dialog).toBeVisible();
    await expect(page.getByText(/deactivate account\?/i)).toBeVisible();

    // Fill password in dialog
    await page.locator('input#deactivate-password').fill(newPassword);

    // Confirm deactivation
    const confirmDeactivateBtn = page.getByRole('button', { name: /yes, deactivate account/i });
    await confirmDeactivateBtn.click();

    // Should redirect to /login
    await page.waitForURL('**/login', { timeout: 10000 });
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText(/account deactivated successfully/i)).toBeVisible({ timeout: 5000 });

    // 9. Verify user cannot login anymore
    const verifyLogin = await fetch(`${apiURL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: updatedUsername,
        password: newPassword,
      }),
    });
    expect(verifyLogin.status).toBe(401);
  });
});
