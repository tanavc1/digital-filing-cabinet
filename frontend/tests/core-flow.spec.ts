import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin';

test.describe('Digital Filing Cabinet Core Flow', () => {

    test('should allow login and redirect to home', async ({ page }) => {
        // 1. Visit Home (should redirect to login)
        await page.goto('/');
        await expect(page).toHaveURL(/\/login/);

        // 2. Fill Password
        await page.getByLabel('Password').fill(ADMIN_PASSWORD);
        await page.getByRole('button', { name: 'Sign In' }).click();

        // 3. Verify Home
        await expect(page).toHaveURL('/');
        await expect(page.getByText('Digital Filing Cabinet')).toBeVisible();
    });

    test('should upload a document and verify ingestion', async ({ page }) => {
        // Setup: Login first
        await page.goto('/login');
        await page.getByLabel('Password').fill(ADMIN_PASSWORD);
        await page.getByRole('button', { name: 'Sign In' }).click();
        await expect(page).toHaveURL('/');

        // 1. Create Dummy PDF
        const testFile = path.join(__dirname, 'test-doc.txt');
        fs.writeFileSync(testFile, 'This is a test document for Playwright E2E testing.');

        // 2. Click Upload (assuming file input is hidden or triggered via button)
        // Note: shadcn upload might need specific handling, but standard input[type=file] works

        // Navigate directly to documents
        await page.goto('/documents');

        // 1. Prepare FileChooser
        const fileChooserPromise = page.waitForEvent('filechooser');

        // 2. Click Upload Button
        await page.getByRole('button', { name: 'Upload Documents' }).click();

        // 3. Set Files
        const fileChooser = await fileChooserPromise;
        await fileChooser.setFiles(testFile);

        // 3. Verify Toast Success
        await expect(page.getByText('uploaded successfully')).toBeVisible({ timeout: 20000 });

        // 4. Verify Document Appears in List (Table Cell)
        // Use .first() to be lenient, or getByRole('cell')
        await expect(page.getByRole('cell', { name: 'test-doc.txt' }).first()).toBeVisible();
    });

    test('should answer questions from uploaded document', async ({ page }) => {
        // Login
        await page.goto('/login');
        await page.getByPlaceholder('Enter password').fill(ADMIN_PASSWORD);
        await page.getByRole('button', { name: 'Login' }).click();

        // 1. Type Query
        const question = "What is this test document for?";
        await page.getByPlaceholder('Ask a question...').fill(question);
        await page.keyboard.press('Enter');

        // 2. Verify Streaming Response
        // Expect "Playwright E2E testing" to appear in the answer
        await expect(page.getByText('Playwright E2E testing', { exact: false })).toBeVisible({ timeout: 15000 });
    });
});
