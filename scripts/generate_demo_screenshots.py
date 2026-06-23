"""
生成演示截图 - 使用 Pillow 创建设计稿作为占位符
"""
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

# 截图保存目录
SCREENSHOT_DIR = Path("docs/images/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 截图配置
SCREENSHOTS = {
    "login": {
        "title": "QueryMind 登录界面",
        "subtitle": "企业级智能问答引擎",
        "features": [
            "🔐 安全认证",
            "🌏 多语言支持",
            "💾 记住我"
        ]
    },
    "chat": {
        "title": "智能问答界面",
        "subtitle": "多智能体协作，实时流式输出",
        "features": [
            "💬 多轮对话",
            "📚 引用溯源",
            "🤖 代理执行可视化",
            "🔍 混合检索"
        ]
    },
    "documents": {
        "title": "文档管理",
        "subtitle": "支持 PDF、图片、文本等多种格式",
        "features": [
            "📄 批量上传",
            "🔍 智能检索",
            "📊 处理状态",
            "🗑️ 文档管理"
        ]
    },
    "knowledge-graph": {
        "title": "知识图谱",
        "subtitle": "实体关系可视化与多跳推理",
        "features": [
            "🕸️ 关系网络",
            "🔎 实体查询",
            "⚡ 交互式探索",
            "📈 图谱分析"
        ]
    },
    "agent-tracking": {
        "title": "代理执行追踪",
        "subtitle": "实时监控多智能体协作流程",
        "features": [
            "🤖 Router → Vector → Graph",
            "⚡ SSE 流式更新",
            "📊 执行统计",
            "🔍 详细日志"
        ]
    },
    "admin-console": {
        "title": "管理控制台",
        "subtitle": "用户管理、系统配置、权限控制",
        "features": [
            "👥 用户管理",
            "🔐 RBAC 权限",
            "⚙️ 系统设置",
            "📋 审计日志"
        ]
    },
    "analytics": {
        "title": "性能分析",
        "subtitle": "检索统计、性能监控、可视化报表",
        "features": [
            "📊 检索统计",
            "⚡ 性能指标",
            "📈 对比分析",
            "🎯 质量评估"
        ]
    }
}

def create_demo_screenshot(name: str, config: dict, width: int = 1920, height: int = 1080):
    """创建演示截图"""
    # 创建图像
    img = Image.new('RGB', (width, height), color=(248, 249, 250))
    draw = ImageDraw.Draw(img)

    # 尝试加载字体
    try:
        title_font = ImageFont.truetype("arial.ttf", 72)
        subtitle_font = ImageFont.truetype("arial.ttf", 36)
        feature_font = ImageFont.truetype("arial.ttf", 32)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        feature_font = ImageFont.load_default()

    # 绘制背景渐变（简化版）
    for i in range(height):
        alpha = i / height
        color = (
            int(248 + (59 - 248) * alpha),
            int(249 +(130 - 249) * alpha),
            int(250 + (246 - 250) * alpha)
        )
        draw.line([(0, i), (width, i)], fill=color)

    # 绘制内容
    y_offset = 300

    # 标题
    title = config["title"]
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(
        ((width - title_width) // 2, y_offset),
        title,
        fill=(31, 41, 55),
        font=title_font
    )

    # 副标题
    y_offset += 120
    subtitle = config["subtitle"]
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    draw.text(
        ((width - subtitle_width) // 2, y_offset),
        subtitle,
        fill=(107, 114, 128),
        font=subtitle_font
    )

    # 功能列表
    y_offset += 120
    for feature in config["features"]:
        feature_bbox = draw.textbbox((0, 0), feature, font=feature_font)
        feature_width = feature_bbox[2] - feature_bbox[0]
        draw.text(
            ((width - feature_width) // 2, y_offset),
            feature,
            fill=(59, 130, 246),
            font=feature_font
        )
        y_offset += 60

    # 添加 QueryMind 标识
    watermark = "QueryMind (智询) - 企业级智能问答引擎"
    watermark_bbox = draw.textbbox((0, 0), watermark, font=subtitle_font)
    watermark_width = watermark_bbox[2] - watermark_bbox[0]
    draw.text(
        ((width - watermark_width) // 2, height - 100),
        watermark,
        fill=(156, 163, 175),
        font=subtitle_font
    )

    # 保存图片
    screenshot_path = SCREENSHOT_DIR / f"{name}.png"
    img.save(screenshot_path, quality=95)
    print(f"✓ 已生成: {screenshot_path}")

def main():
    print("=" * 60)
    print("  QueryMind 演示截图生成工具")
    print("=" * 60)
    print()

    for name, config in SCREENSHOTS.items():
        print(f"📸 生成 {name}...")
        create_demo_screenshot(name, config)

    print()
    print("✅ 所有演示截图已生成！")
    print(f"   保存位置: {SCREENSHOT_DIR.absolute()}")
    print()
    print("💡 提示: 这些是演示用的占位图片")
    print("   如需真实截图，请运行应用后使用 auto_screenshot.py")

if __name__ == "__main__":
    import sys
    import io
    # 设置UTF-8编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()
