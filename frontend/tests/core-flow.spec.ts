import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin';

test.describe('Digital Filing Cabinet Core Flow', () => {

    test('Complete User Journey (Login -> Upload -> Chat)', async ({ page }) => {
        // --- 1. LOGIN ---
        console.log('Step 1: Login');
        await page.goto('/');
        await expect(page).toHaveURL(/\/login/);

        await page.getByLabel('Password').fill(ADMIN_PASSWORD);
        await page.getByRole('button', { name: 'Sign In' }).click();

        await expect(page).toHaveURL('/');
        await expect(page.getByText('Digital Filing Cabinet')).toBeVisible();

        // --- 2. UPLOAD ---
        console.log('Step 2: Upload');
        // Create dummy file
        const testFile = path.join(__dirname, 'test-doc.txt');
        fs.writeFileSync(testFile, 'This is a test document for Playwright E2E testing. It confirms that the RAG pipeline is working.');

        // Navigate to documents
        await page.goto('/documents');

        // Handle file chooser
        const fileChooserPromise = page.waitForEvent('filechooser');

        // Click Upload (ensure we wait for it to be actionable)
        await page.getByRole('button', { name: 'Upload Documents' }).click();

        const fileChooser = await fileChooserPromise;
        await fileChooser.setFiles(testFile);

        // Verify Success Toast (Generic match for "uploaded")
        await expect(page.getByText('uploaded successfully')).toBeVisible({ timeout: 15000 });

        // Verify in Table
        await expect(page.getByRole('cell', { name: 'test-doc.txt' }).first()).toBeVisible();

        // --- 3. CHAT ---
        console.log('Step 3: Chat');
        await page.goto('/');

        // Wait for input to be ready
        // Placeholder is dynamic like "Message Main...", so use getByPlaceholder(/Message/) regex
        const input = page.getByPlaceholder(/Message/);
        await expect(input).toBeVisible();

        await input.fill("What is the purpose of this test document?");
        await page.keyboard.press('Enter');

        // Verify Answer contains key phrase from our dummy doc
        // "Playwright E2E testing"
        await expect(page.getByText('Playwright', { exact: false })).toBeVisible({ timeout: 20000 });
    });
});
