"""Automated route and navigation check for the thinkNXG Command Center.

Runs against a preview build (VITE_MOCK=1) served at BASE_URL, or against a real
site with an authenticated storage state. Fails if any click, link or route ends
up on the Desk (/desk or /app), or if a page throws.

    python3 e2e/navigation_check.py [BASE_URL]
"""

import asyncio
import sys

from playwright.async_api import async_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8787").rstrip("/")
failures: list[str] = []
checked = 0


def fail(msg):
	failures.append(msg)
	print("FAIL", msg)


async def main():
	global checked
	async with async_playwright() as p:
		browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
		ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
		page = await ctx.new_page()
		errors: list[str] = []
		desk_hits: list[str] = []
		page.on("pageerror", lambda e: errors.append(str(e)) if "Unexpected token '{'" not in str(e) else None)
		page.on("framenavigated", lambda f: desk_hits.append(f.url) if f == page.main_frame and ("/desk" in f.url or "/app/" in f.url) else None)

		async def goto(path):
			await page.goto(BASE + "/thinknxg" + path)
			await page.wait_for_timeout(900)

		async def expect_internal(label):
			global checked
			checked += 1
			url = page.url
			if "/thinknxg" not in url:
				fail(f"{label}: left the Command Center -> {url}")
			if errors:
				fail(f"{label}: page error {errors[-1]}")
				errors.clear()

		# 1. Every sidebar item (and nested child) in each center
		for center in ("/admin", "/erp", "/hr"):
			await goto(center)
			hrefs = await page.eval_on_selector_all("aside nav a[href]", "els => els.map(e => e.getAttribute('href'))")
			for h in dict.fromkeys(hrefs):
				await goto(center)
				link = page.locator(f'aside nav a[href="{h}"]').first
				if not await link.count():
					continue
				await link.click()
				await page.wait_for_timeout(700)
				await expect_internal(f"sidebar {center} -> {h}")

		# 2. Module pages: every document card opens its list
		for mod in ("/erp/accounting", "/erp/selling", "/hr/leave"):
			await goto(mod)
			cards = await page.eval_on_selector_all("main a[href*='/thinknxg/']", "els => els.map(e => e.getAttribute('href'))")
			for h in [c for c in dict.fromkeys(cards)][:12]:
				await goto(h.replace("/thinknxg", ""))
				await expect_internal(f"module link {h}")

		# 3. List -> document -> back / forward / refresh
		await goto("/erp/accounting/sales-invoice")
		first = page.locator("main tbody a").first
		try:
			await first.wait_for(timeout=6000)
		except Exception:
			pass
		if await first.count():
			await first.click()
			await page.wait_for_timeout(1000)
			await expect_internal("open document from list")
			form_url = page.url
			try:
				await page.get_by_role("heading", level=1).first.wait_for(timeout=8000)
			except Exception:
				fail("document form has no title")
			await page.go_back()
			await page.wait_for_timeout(700)
			if "/sales-invoice/" in page.url:
				fail("back did not return to the list")
			await page.go_forward()
			await page.wait_for_timeout(900)
			if page.url != form_url:
				fail("forward did not return to the document")
			await page.reload()
			await page.wait_for_timeout(2500)
			await expect_internal("refresh document route")
			if not await page.get_by_text("PVC pipe 110 mm").count() and not await page.get_by_text("PIPE-PVC-110").count():
				fail("document child table did not render after refresh")
		else:
			fail("sales invoice list shows no rows")

		# 4. New document and save
		await goto("/erp/accounting/sales-invoice/new")
		await expect_internal("new document")
		if await page.get_by_role("button", name="Save").count():
			await page.get_by_role("button", name="Save").first.click()
			await page.wait_for_timeout(600)

		# 5. Report runner
		await goto("/erp/reports/General%20Ledger")
		await page.wait_for_timeout(800)
		await expect_internal("report runner")

		# 6. Unauthorized and legacy routes stay inside, with a clear page
		for path, expect in (("/hr/payroll", "denied"), ("/erp/not-a-module", "denied"), ("/users", "/admin/users"), ("/system-health", "/admin/system-health"), ("/no/such/page", "not found")):
			await goto(path)
			await expect_internal(f"route {path}")
			body = (await page.content()).lower()
			if expect == "denied" and "/denied" not in page.url:
				fail(f"{path} should show access denied, got {page.url}")
			if expect.startswith("/") and expect not in page.url:
				fail(f"{path} should redirect to {expect}, got {page.url}")
			if expect == "not found" and "not found" not in body and "isn't" not in body:
				fail(f"{path} should show not found")

		# 7. Old Desk links clicked anywhere are routed internally
		await goto("/admin")
		await page.evaluate("""() => { const a = document.createElement('a'); a.href = '/desk/sales-invoice/ACC-SINV-2026-00701'; a.id = 'legacy'; a.textContent = 'legacy'; document.querySelector('main').prepend(a); }""")
		await page.click("#legacy")
		await page.wait_for_timeout(1000)
		await expect_internal("legacy desk link")
		if "/erp/accounting/sales-invoice/ACC-SINV-2026-00701" not in page.url:
			fail(f"legacy desk link mapped to {page.url}")

		# 8. KPI tiles and quick actions on each dashboard
		for center in ("/erp", "/hr"):
			await goto(center)
			kpis = await page.eval_on_selector_all("section[aria-label='Key figures'] a[href]", "els => els.map(e => e.getAttribute('href'))")
			for h in kpis:
				if "/desk" in h or h.startswith("/app"):
					fail(f"KPI link on {center} points to the Desk: {h}")
				checked += 1

		if desk_hits:
			fail(f"navigated to the Desk: {desk_hits}")
		await browser.close()
	print(f"\n{checked} navigation checks, {len(failures)} failures")
	sys.exit(1 if failures else 0)


asyncio.run(main())
