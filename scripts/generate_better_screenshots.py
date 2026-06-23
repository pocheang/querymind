"""
生成更专业的演示截图 - 使用更好的设计和布局
"""
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

SCREENSHOT_DIR = Path("docs/images/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def create_professional_screenshot(name: str, title: str, elements: list, width: int = 1920, height: int = 1080):
    """创建专业的演示截图"""
    # 创建图像 - 使用应用配色
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 尝试加载字体
    try:
        title_font = ImageFont.truetype("arial.ttf", 48)
        text_font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 18)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # 绘制顶部导航栏
    draw.rectangle([(0, 0), (width, 80)], fill=(59, 130, 246))

    # QueryMind logo
    draw.text((40, 25), "QueryMind", fill=(255, 255, 255), font=title_font)

    # 绘制主要内容区域
    content_y = 120

    # 标题
    draw.text((60, content_y), title, fill=(31, 41, 55), font=title_font)
    content_y += 80

    # 绘制元素
    for element in elements:
        if element['type'] == 'box':
            # 绘制卡片/框
            x, y, w, h = element['x'], content_y, element['width'], element['height']
            draw.rectangle([(x, y), (x + w, y + h)], outline=(229, 231, 235), fill=(249, 250, 251), width=2)

            # 卡片标题
            if 'title' in element:
                draw.text((x + 20, y + 20), element['title'], fill=(31, 41, 55), font=text_font)

            # 卡片内容
            if 'content' in element:
                text_y = y + 60
                for line in element['content']:
                    draw.text((x + 20, text_y), line, fill=(107, 114, 128), font=small_font)
                    text_y += 30

            content_y += h + 30

        elif element['type'] == 'text':
            draw.text((60, content_y), element['text'], fill=(75, 85, 99), font=text_font)
            content_y += 40

    # 底部水印
    watermark = "QueryMind (智询) - 企业级智能问答引擎"
    draw.text((60, height - 50), watermark, fill=(156, 163, 175), font=small_font)

    # 保存
    screenshot_path = SCREENSHOT_DIR / f"{name}.png"
    img.save(screenshot_path, quality=95)
    print(f"✓ 已生成: {screenshot_path}")

def main():
    print("=" * 60)
    print("  生成专业演示截图")
    print("=" * 60)
    print()

    # 1. 登录页面 - 跳过，已有真实截图
    print("✓ login.png - 使用真实截图")

    # 2. 聊天界面
    print("📸 生成 chat.png...")
    create_professional_screenshot("chat", "智能问答", [
        {'type': 'box', 'x': 60, 'width': 800, 'height': 200, 'title': '用户提问',
         'content': ['QueryMind 有哪些核心功能？']},
        {'type': 'box', 'x': 60, 'width': 800, 'height': 300, 'title': 'AI 回答',
         'content': [
             '✓ 多智能体协作 - 智能路由和任务分配',
             '✓ 混合检索 - 向量检索 + BM25 + 重排序',
             '✓ 知识图谱增强 - Neo4j 实体关系查询',
             '✓ 实时监控 - 代理执行可视化',
             '',
             '引用来源: [文档1] [文档2]'
         ]},
    ])

    # 3. 文档管理
    print("📸 生成 documents.png...")
    create_professional_screenshot("documents", "文档管理", [
        {'type': 'text', 'text': '已上传文档 (15)'},
        {'type': 'box', 'x': 60, 'width': 1800, 'height': 400, 'title': '文档列表',
         'content': [
             '📄 产品白皮书.pdf - 2.3 MB - 已处理 ✓',
             '📄 技术文档.pdf - 1.8 MB - 已处理 ✓',
             '📄 用户手册.docx - 850 KB - 处理中...',
             '🖼️ 架构图.png - 450 KB - 已处理 ✓',
             '📄 API文档.md - 120 KB - 已处理 ✓',
         ]},
    ])

    # 4. 知识图谱
    print("📸 生成 knowledge-graph.png...")
    create_professional_screenshot("knowledge-graph", "知识图谱可视化", [
        {'type': 'text', 'text': '实体关系网络 - 显示 128 个节点, 245 个关系'},
        {'type': 'box', 'x': 60, 'width': 1800, 'height': 600, 'title': '图谱视图',
         'content': [
             '',
             '         [产品A] ──关联→ [功能1]',
             '            │',
             '            ↓',
             '         [技术栈] ──依赖→ [框架B]',
             '            │',
             '            ↓',
             '         [应用场景] ──适用于→ [场景C]',
             '',
             '🔍 点击节点查看详情 | ⚡ 多跳推理支持'
         ]},
    ])

    # 5. 代理追踪
    print("📸 生成 agent-tracking.png...")
    create_professional_screenshot("agent-tracking", "代理执行追踪", [
        {'type': 'text', 'text': '实时监控 - 查询ID: query_20260623_001'},
        {'type': 'box', 'x': 60, 'width': 1800, 'height': 500, 'title': '执行流程',
         'content': [
             '1. ✓ Router Agent - 查询意图分析 (120ms)',
             '   └─ 判定: 需要混合检索 + 知识图谱',
             '',
             '2. ✓ Vector RAG Agent - 向量检索 (350ms)',
             '   └─ 检索到 15 个相关文档',
             '',
             '3. ✓ Graph RAG Agent - 图谱查询 (280ms)',
             '   └─ 找到 8 个相关实体关系',
             '',
             '4. ⏳ Synthesis Agent - 答案合成中...',
         ]},
    ])

    # 6. 管理控制台
    print("📸 生成 admin-console.png...")
    create_professional_screenshot("admin-console", "管理控制台", [
        {'type': 'text', 'text': '系统概览'},
        {'type': 'box', 'x': 60, 'width': 850, 'height': 300, 'title': '用户管理',
         'content': [
             '总用户数: 45',
             '活跃用户: 32',
             '管理员: 3',
             '分析师: 15',
             '观察者: 27',
         ]},
        {'type': 'box', 'x': 960, 'width': 850, 'height': 300, 'title': '系统状态',
         'content': [
             '服务状态: 运行中 ✓',
             '数据库连接: 正常 ✓',
             'Redis 缓存: 正常 ✓',
             'Neo4j 图库: 正常 ✓',
             '内存使用: 2.3 GB / 8 GB',
         ]},
    ])

    # 7. 性能分析
    print("📸 生成 analytics.png...")
    create_professional_screenshot("analytics", "性能分析", [
        {'type': 'text', 'text': '检索统计 - 最近 7 天'},
        {'type': 'box', 'x': 60, 'width': 1800, 'height': 500, 'title': '性能指标',
         'content': [
             '查询总数: 1,247',
             '平均响应时间: 850ms',
             '检索准确率 (Precision): 0.89',
             '检索召回率 (Recall): 0.92',
             'F1 Score: 0.90',
             'NDCG@10: 0.88',
             '',
             '最常用功能: 向量检索 (65%), 混合检索 (25%), 知识图谱 (10%)',
         ]},
    ])

    print()
    print("✅ 所有演示截图已生成！")
    print(f"   保存位置: {SCREENSHOT_DIR.absolute()}")

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()
