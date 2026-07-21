import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

const BASE_URL = process.env.BASE_URL ?? 'https://app.vwo.com';

test.describe('login', () => {
  test('valid login lands on dashboard', async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto(BASE_URL);
    await login.signIn('qa@example.com', 'secret');
    await expect(page.getByTestId('dashboard-title')).toBeVisible();
  });
});

export async function waitForCouponBanner(page) {
  await page.waitForSelector('#coupon-input', { state: 'visible', timeout: 5000 });
}
