"""Playwright test for Advanced RAG Explorer - headed browser mode"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import os
import sys

CSV_PATH = r"D:\AI 3x Blueprint\Practice_2\chapter_07_RAG_advance\testcase\vwo_test_cases_5000.csv"
BASE_URL = "http://127.0.0.1:5050"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        errors = []

        # --- Step 1: Open app, verify /upload loads ---
        print("[STEP 1] Opening app at /upload...")
        try:
            await page.goto(f"{BASE_URL}/upload", wait_until="networkidle", timeout=30000)
            await page.wait_for_selector('h1:has-text("Upload Test Cases")', timeout=10000)
            print("  ✓ Home page loaded, h1 found")
        except Exception as e:
            errors.append(f"Step 1 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 2: Upload CSV file ---
        print("[STEP 2] Uploading CSV file...")
        try:
            # Use the file input
            file_input = page.locator('input[type="file"]')
            await file_input.wait_for(timeout=5000)
            await file_input.set_input_files(CSV_PATH)
            print("  ✓ File selected")
        except Exception as e:
            errors.append(f"Step 2 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 3: Click "Upload & Preview" ---
        print("[STEP 3] Clicking Upload & Preview...")
        try:
            upload_btn = page.locator('button:has-text("Upload & Preview")')
            await upload_btn.click()
            await page.wait_for_timeout(2000)
            print("  ✓ Upload & Preview clicked")
        except Exception as e:
            errors.append(f"Step 3 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 4: Verify preview loaded ---
        print("[STEP 4] Verifying preview loaded...")
        try:
            await page.wait_for_selector('text=Preview', timeout=15000)
            await page.wait_for_selector('text=5000 rows', timeout=5000)
            print("  ✓ Preview section visible with 5000 rows")

            # Check columns
            await page.wait_for_selector('text=Columns', timeout=3000)
            print("  ✓ Columns shown")

            # Check data types table
            await page.wait_for_selector('text=Data types', timeout=3000)
            dtypes = page.locator('table:has(th:has-text("Data types"))')
            print("  ✓ Data types table visible")

            # Check first 5 rows table
            await page.wait_for_selector('text=First 5 Rows', timeout=3000)
            print("  ✓ First 5 rows table visible")
        except Exception as e:
            errors.append(f"Step 4 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 5: Select text columns ---
        print("[STEP 5] Selecting text columns...")
        try:
            text_select = page.locator('select[name="text_cols"]')
            await text_select.wait_for(timeout=5000)
            # Clear any selection first
            await text_select.click()
            # Select all desired text columns
            text_cols = ["title", "steps", "expected", "description", "preconditions", "tags"]
            for col in text_cols:
                await text_select.select_option(col, timeout=3000)
                await page.wait_for_timeout(200)
            print(f"  ✓ Text columns selected: {text_cols}")
        except Exception as e:
            errors.append(f"Step 5 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 6: Select metadata columns ---
        print("[STEP 6] Selecting metadata columns...")
        try:
            meta_select = page.locator('select[name="meta_cols"]')
            await meta_select.wait_for(timeout=5000)
            await meta_select.click()
            meta_cols = ["id", "jira_id", "priority", "module"]
            for col in meta_cols:
                await meta_select.select_option(col, timeout=3000)
                await page.wait_for_timeout(200)
            print(f"  ✓ Metadata columns selected: {meta_cols}")
        except Exception as e:
            errors.append(f"Step 6 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 7: Click Start Ingestion ---
        print("[STEP 7] Clicking Start Ingestion...")
        try:
            ingest_btn = page.locator('button:has-text("Start Ingestion")')
            await ingest_btn.scroll_into_view_if_needed()
            await ingest_btn.click()
            await page.wait_for_timeout(3000)
            print("  ✓ Start Ingestion clicked")
        except Exception as e:
            errors.append(f"Step 7 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 8: Wait for ingestion monitoring page ---
        print("[STEP 8] Waiting for ingestion monitoring page...")
        try:
            await page.wait_for_selector('h1:has-text("Ingesting")', timeout=30000)
            print("  ✓ Ingestion monitoring page loaded")

            # Wait for pipeline progress elements
            await page.wait_for_selector('[data-stage="warm"]', timeout=5000)
            await page.wait_for_selector('[data-stage="read"]', timeout=5000)
            await page.wait_for_selector('[data-stage="build"]', timeout=5000)
            await page.wait_for_selector('[data-stage="chunk"]', timeout=5000)
            await page.wait_for_selector('[data-stage="embed"]', timeout=5000)
            await page.wait_for_selector('[data-stage="index"]', timeout=5000)
            print("  ✓ All 6 pipeline stages visible")
        except Exception as e:
            errors.append(f"Step 8 failed: {e}")
            print(f"  ✗ {e}")

        # --- Step 9: Monitor for errors during ingestion ---
        print("[STEP 9] Monitoring ingestion for errors (60s timeout)...")
        try:
            # Wait for either completion or error flash messages
            await page.wait_for_selector('#complete-card, .flash.error', timeout=120000)
            
            # Check for error messages
            error_flash = page.locator('.flash.error')
            error_count = await error_flash.count()
            if error_count > 0:
                error_texts = []
                for i in range(error_count):
                    text = await error_flash.nth(i).text_content()
                    error_texts.append(text)
                errors.append(f"Ingestion errors found: {error_texts}")
                print(f"  ✗ Errors detected: {error_texts}")
            else:
                print("  ✓ No flash errors detected")

            # Check completion
            complete = page.locator('#complete-card')
            if await complete.is_visible():
                msg = await page.locator('#complete-message').text_content()
                print(f"  ✓ Ingestion completed: {msg}")
            else:
                print("  ⚠ Ingestion may still be in progress or complete card not visible")
                
        except PlaywrightTimeout:
            # Check page for any error text
            page_text = await page.text_content('body')
            if "error" in page_text.lower() or "Error" in page_text:
                errors.append("Timed out waiting for ingestion completion - errors may exist on page")
                print("  ✗ Timed out - errors may exist on page")
            else:
                print("  ⚠ Timed out waiting - ingestion may be running long")
        except Exception as e:
            errors.append(f"Step 9 failed: {e}")
            print(f"  ✗ {e}")

        # --- Summary ---
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        if errors:
            print(f"ERRORS FOUND ({len(errors)}):")
            for i, err in enumerate(errors, 1):
                print(f"  {i}. {err}")
        else:
            print("✓ No errors detected!")
        print("="*60)

        await page.wait_for_timeout(5000)  # Keep browser open briefly
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
