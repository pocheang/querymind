"""
完整的自动截图脚本 - 包括登录和注册界面
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

SCREENSHOT_DIR = Path("docs/images/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:5173"

async def take_screenshot(page, name: str):
    """截取当前页面"""
    screenshot_path = SCREENSHOT_DIR / f"{name}.png"
    await page.screenshot(path=str(screenshot_path), full_page=False)
    print(f"✓ 已保存: {name}.png")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        print("🚀 开始截图...")
        print()

        # 1. 登录页面
        print("📸 1/8 登录界面...")
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        await take_screenshot(page, "login")

        # 2. 注册页面 - 尝试切换到注册
        print("📸 2/8 注册界面...")
        try:
            # 尝试多种可能的注册按钮选择器
            register_selectors = [
                'text=注册',
                'text=Register',
                'text=Sign Up',
                'a:has-text("注册")',
                'button:has-text("注册")',
                '[href*="register"]',
                '.auth-form button:nth-child(2)'
            ]

            for selector in register_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        await asyncio.sleep(2)
                        await take_screenshot(page, "register")
                        print("  ✓ 注册界面截图成功")
                        break
                except:
                    continue
            else:
                print("  ⚠️ 未找到注册按钮，跳过")
        except Exception as e:
            print(f"  ⚠️ 注册界面截图失败: {e}")

        # 3. 尝试注册或登录
        print()
        print("🔐 尝试登录...")

        # 回到登录页面
        await page.goto(BASE_URL)
        await asyncio.sleep(2)

        try:
            # 尝试填写登录表单
            username_selectors = [
                'input[placeholder*="用户名"]',
                'input[placeholder*="username"]',
                'input[name="username"]',
                'input[id="username"]',
                'input[type="text"]'
            ]

            password_selector = 'input[type="password"]'

            # 填写用户名
            for selector in username_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.fill("admin")
                        break
                except:
                    continue

            # 填写密码
            await page.locator(password_selector).first.fill("admin")

            # 提交
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("登录")',
                'button:has-text("Login")'
            ]

            for selector in submit_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        await element.click()
                        break
                except:
                    continue

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)

            # 检查是否登录成功
            if "/chat" in page.url or "/dashboard" in page.url or page.url == BASE_URL + "/":
                print("  ✓ 登录成功")

                # 3. 聊天界面
                print("📸 3/8 聊天界面...")
                await page.goto(f"{BASE_URL}/chat")
                await asyncio.sleep(2)
                await take_screenshot(page, "chat")

                # 4. 文档管理
                print("📸 4/8 文档管理...")
                await page.goto(f"{BASE_URL}/documents")
                await asyncio.sleep(2)
                await take_screenshot(page, "documents")

                # 5. 知识图谱
                print("📸 5/8 知识图谱...")
                try:
                    await page.goto(f"{BASE_URL}/knowledge-graph")
                    await asyncio.sleep(2)
                    await take_screenshot(page, "knowledge-graph")
                except:
                    print("  ⚠️ 知识图谱页面不可用")

                # 6. 代理追踪
                print("📸 6/8 代理追踪...")
                try:
                    await page.goto(f"{BASE_URL}/agent-tracking")
                    await asyncio.sleep(2)
                    await take_screenshot(page, "agent-tracking")
                except:
                    print("  ⚠️ 代理追踪页面不可用")

                # 7. 管理控制台
                print("📸 7/8 管理控制台...")
                try:
                    await page.goto(f"{BASE_URL}/admin")
                    await asyncio.sleep(2)
                    await take_screenshot(page, "admin-console")
                except:
                    print("  ⚠️ 管理控制台页面不可用")

                # 8. 性能分析
                print("📸 8/8 性能分析...")
                try:
                    await page.goto(f"{BASE_URL}/analytics")
                    await asyncio.sleep(2)
                    await take_screenshot(page, "analytics")
                except:
                    print("  ⚠️ 性能分析页面不可用")

            else:
                print("  ⚠️ 登录失败，无法截取登录后页面")
                print(f"  当前URL: {page.url}")

        except Exception as e:
            print(f"  ⚠️ 登录过程出错: {e}")

        await browser.close()

        print()
        print("=" * 60)
        print("✅ 截图完成！")
        print(f"保存位置: {SCREENSHOT_DIR.absolute()}")
        print()

if __name__ == "__main__":
    print("=" * 60)
    print("  QueryMind 完整截图工具")
    print("=" * 60)
    print()
    asyncio.run(main())
