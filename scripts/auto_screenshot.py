"""
自动截图脚本 - 为 QueryMind 项目生成演示截图
使用 Playwright 自动化浏览器截图
"""
import asyncio
from playwright.async_api import async_playwright
import os
from pathlib import Path

# 截图保存目录
SCREENSHOT_DIR = Path("docs/images/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 应用 URL
BASE_URL = "http://localhost:5173"

async def take_screenshot(page, name: str, selector: str = None, full_page: bool = False):
    """截取页面或元素截图"""
    screenshot_path = SCREENSHOT_DIR / f"{name}.png"

    if selector:
        element = await page.locator(selector).first
        await element.screenshot(path=str(screenshot_path))
    else:
        await page.screenshot(path=str(screenshot_path), full_page=full_page)

    print(f"✓ 已保存截图: {screenshot_path}")

async def main():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2  # 高清截图
        )
        page = await context.new_page()

        print("🚀 开始自动截图...")

        # 1. 登录页面
        print("\n📸 截取登录页面...")
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)  # 等待动画完成
        await take_screenshot(page, "login", full_page=True)

        # 尝试登录（如果有默认账号）
        try:
            # 填写登录表单
            await page.fill('input[type="text"]', 'admin')
            await page.fill('input[type="password"]', 'admin123')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            # 2. 聊天页面
            print("\n📸 截取聊天页面...")
            await page.goto(f"{BASE_URL}/chat")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            # 模拟输入查询
            query_input = page.locator('textarea, input[placeholder*="问题"]').first
            if await query_input.count() > 0:
                await query_input.fill("QueryMind 有哪些核心功能？")
                await asyncio.sleep(1)

            await take_screenshot(page, "chat", full_page=True)

            # 3. 文档管理页面
            print("\n📸 截取文档管理页面...")
            await page.goto(f"{BASE_URL}/documents")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await take_screenshot(page, "documents", full_page=True)

            # 4. 管理控制台
            print("\n📸 截取管理控制台...")
            await page.goto(f"{BASE_URL}/admin")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await take_screenshot(page, "admin-console", full_page=True)

            # 5. 性能分析页面
            print("\n📸 截取性能分析页面...")
            await page.goto(f"{BASE_URL}/analytics")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await take_screenshot(page, "analytics", full_page=True)

        except Exception as e:
            print(f"⚠️  登录后页面截图失败: {e}")
            print("   请确保应用正在运行且账号正确")

        await browser.close()
        print("\n✅ 截图完成！")
        print(f"   保存位置: {SCREENSHOT_DIR.absolute()}")

if __name__ == "__main__":
    print("=" * 60)
    print("  QueryMind 自动截图工具")
    print("=" * 60)
    print("\n请确保:")
    print("1. 应用正在运行 (http://localhost:5173)")
    print("2. 已安装 Playwright: pip install playwright")
    print("3. 已安装浏览器: playwright install chromium")
    print()

    asyncio.run(main())
