# 代码可视化工具快速指南

## 🎯 快速开始

### 一键生成所有可视化
```bash
python scripts/visualize_all.py
```

### 只生成交互式仪表板（推荐）
```bash
python scripts/visualize_dashboard.py
# 在浏览器中打开 docs/dashboard.html
```

---

## 📊 可视化工具列表

| 工具 | 输出文件 | 描述 |
|------|---------|------|
| `visualize_dashboard.py` | `docs/dashboard.html` | 🌟 交互式仪表板（带图表） |
| `visualize_html.py` | `docs/structure_visualization.html` | HTML报告 |
| `visualize_text.py` | `docs/structure_report.txt` | 文本报告 |
| `visualize_dependencies.py` | `docs/visualizations/*.dot` | 依赖关系图 |
| `visualize_all.py` | 所有上述文件 | 一键生成全部 |

---

## 📈 当前项目统计

- **352** 个Python文件
- **52,916** 行代码
- **97** 个测试文件
- **主要模块**: app (209), tests (89), scripts (49)

---

## 🔍 其他可视化方法

### 方法1: VS Code扩展
- **Code Map** - 代码结构可视化
- **Dependency Cruiser** - 依赖分析

### 方法2: Python包
```bash
# 生成依赖图
pip install pydeps
pydeps app --max-bacon=2 -o docs/pydeps.svg

# 生成UML类图
pip install pylint
pyreverse -o png -p MultiAgentRAG app/
```

### 方法3: 在线工具
- **Code2flow** - 流程图生成
- **Sourcegraph** - 代码搜索和可视化

---

## 💡 查看详细指南
完整文档请查看: [VISUALIZATION_GUIDE.md](./VISUALIZATION_GUIDE.md)
