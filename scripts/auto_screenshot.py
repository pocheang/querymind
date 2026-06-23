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

    # 标准截图，不使用 full_page，避免超长截图
    if selector:
        element = await page.locator(selector).first
        await element.screenshot(path=str(screenshot_path))
    else:
        # 只截取可见视口，不滚动整个页面
        await page.screenshot(path=str(screenshot_path), full_page=False)

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

        # 尝试注册新账号并登录
        try:
            print("\n🔐 注册测试账号...")
            # 切换到注册模式
            register_button = page.locator('text=注册, text=Register, text=Sign Up').first
            if await register_button.count() > 0:
                await register_button.click()
                await asyncio.sleep(1)

            # 填写注册表单
            username = "demo_user"
            password = "Demo123456"

            # 尝试多种选择器
            username_input = page.locator('input[placeholder*="用户名"], input[placeholder*="username"], input[name="username"], input[id="username"]').first
            password_input = page.locator('input[type="password"]').first
            confirm_input = page.locator('input[placeholder*="确认"], input[placeholder*="confirm"]').first

            await username_input.fill(username)
            await password_input.fill(password)

            # 如果有确认密码框
            if await confirm_input.count() > 0:
                await confirm_input.fill(password)

            # 提交注册
            submit_button = page.locator('button[type="submit"], button:has-text("注册"), button:has-text("Register")').first
            await submit_button.click()
            await asyncio.sleep(3)

            # 如果注册成功，可能需要重新登录
            # 检查是否还在登录页面
            if "login" in page.url.lower() or await page.locator('input[type="password"]').count() > 0:
                print("🔐 使用新账号登录...")
                await username_input.fill(username)
                await password_input.fill(password)
                await submit_button.click()

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
