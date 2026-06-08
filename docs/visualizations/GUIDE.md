# 代码结构可视化工具指南

本项目提供了多种可视化代码结构的工具和方法。所有工具都位于 `scripts/` 目录下。

## 📊 可用的可视化工具

### 1. 交互式仪表板 (推荐)
**文件**: `scripts/visualize_dashboard.py`

生成一个带有图表的交互式HTML仪表板，包含：
- 项目统计概览（文件数、代码行数、测试文件、函数、类）
- 模块分布柱状图
- 代码行数分布饼图
- 最大文件排行表

**使用方法**:
```bash
python scripts/visualize_dashboard.py
```

**输出**: `docs/dashboard.html` - 在浏览器中打开查看

---

### 2. 简化HTML可视化
**文件**: `scripts/visualize_html.py`

生成一个美观的HTML报告，包含：
- 项目统计卡片
- 模块分布条形图
- 最大文件表格
- 最常被导入的模块分析

**使用方法**:
```bash
python scripts/visualize_html.py
```

**输出**: `docs/structure_visualization.html`

---

### 3. 文本版结构报告
**文件**: `scripts/visualize_text.py`

生成纯文本格式的项目结构分析报告，适合：
- 快速查看项目概况
- 命令行环境
- 文档记录

**使用方法**:
```bash
python scripts/visualize_text.py
```

**输出**: 
- 控制台输出
- `docs/structure_report.txt`

---

### 4. 依赖关系图 (Graphviz)
**文件**: `scripts/visualize_dependencies.py`

生成模块依赖关系的Graphviz DOT文件，包括：
- 模块间的导入依赖关系图
- 模块树结构图

**使用方法**:
```bash
# 生成DOT文件
python scripts/visualize_dependencies.py

# 转换为图片（需要安装Graphviz）
dot -Tpng docs/visualizations/dependencies.dot -o docs/visualizations/dependencies.png
dot -Tsvg docs/visualizations/module_tree.dot -o docs/visualizations/module_tree.svg
```

**要求**: 需要安装 [Graphviz](https://graphviz.org/download/)

**输出**: 
- `docs/visualizations/dependencies.dot` - 依赖关系图
- `docs/visualizations/module_tree.dot` - 模块树结构图

---

## 🎯 快速开始

### 方法1: 一次性生成所有可视化

```bash
# 生成所有可视化报告
python scripts/visualize_dashboard.py
python scripts/visualize_html.py
python scripts/visualize_text.py
python scripts/visualize_dependencies.py
```

### 方法2: 只生成交互式仪表板（最推荐）

```bash
python scripts/visualize_dashboard.py
# 然后在浏览器中打开 docs/dashboard.html
```

---

## 📂 输出文件位置

所有可视化输出文件都保存在以下位置：

```
docs/
├── dashboard.html                      # 交互式仪表板（推荐）
├── structure_visualization.html        # HTML可视化报告
├── structure_report.txt                # 文本格式报告
└── visualizations/
    ├── dependencies.dot                # 依赖关系DOT文件
    ├── dependencies.png                # 依赖关系图（需要Graphviz）
    ├── module_tree.dot                 # 模块树DOT文件
    └── module_tree.png                 # 模块树图（需要Graphviz）
```

---

## 🔍 每种工具的优势

### 交互式仪表板 (`visualize_dashboard.py`)
✅ 最全面的可视化  
✅ 使用Chart.js的交互式图表  
✅ 美观的现代化界面  
✅ 适合展示和报告  

### HTML可视化 (`visualize_html.py`)
✅ 详细的统计信息  
✅ 导入关系分析  
✅ 无需额外依赖  
✅ 适合技术文档  

### 文本报告 (`visualize_text.py`)
✅ 最快速  
✅ 无编码问题  
✅ 适合命令行  
✅ 易于集成到CI/CD  

### 依赖关系图 (`visualize_dependencies.py`)
✅ 可视化模块依赖  
✅ 发现紧密耦合的模块  
✅ 架构分析  
✅ 需要Graphviz  

---

## 🛠️ 其他可视化工具推荐

### VS Code 扩展
- **Python Test Explorer** - 可视化测试结构
- **Code Map** - 代码地图可视化
- **Dependency Graph** - 依赖关系图

### Python包
```bash
# 安装其他可视化工具
pip install pydeps         # 生成依赖关系图
pip install pyreverse      # UML类图生成器（pylint的一部分）
pip install snakeviz       # 性能分析可视化
```

### 使用pydeps生成依赖图
```bash
pip install pydeps
pydeps app --max-bacon=2 -o docs/pydeps.svg
```

### 使用pyreverse生成UML图
```bash
pip install pylint
pyreverse -o png -p MultiAgentRAG app/
```

---

## 📊 项目当前统计

根据最新分析（2026-06-03）：

- **总Python文件**: 352个
- **总代码行数**: 52,916行
- **测试文件**: 97个
- **主要模块**: app (209文件), tests (89文件), scripts (49文件)

### 最大的文件Top 5:
1. `tests/integration/test_multilingual_workflow.py` - 907行
2. `app/api/routes/query.py` - 906行
3. `tests/test_memory_api.py` - 659行
4. `app/api/routes/admin_ops.py` - 625行
5. `tests/services/test_retrieval_logger.py` - 613行

---

## 💡 使用建议

1. **日常开发**: 使用 `visualize_text.py` 快速查看项目概况
2. **代码审查**: 使用 `visualize_dashboard.py` 生成完整报告
3. **架构分析**: 使用 `visualize_dependencies.py` 分析模块依赖
4. **文档生成**: 使用 `visualize_html.py` 生成技术文档

---

## 🔄 自动化

可以将可视化工具集成到CI/CD流程中：

```yaml
# .github/workflows/visualize.yml
name: Generate Structure Visualization
on: [push]
jobs:
  visualize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Generate visualizations
        run: |
          python scripts/visualize_dashboard.py
          python scripts/visualize_text.py
      - name: Upload artifacts
        uses: actions/upload-artifact@v2
        with:
          name: visualizations
          path: docs/
```

---

## 📝 维护说明

这些可视化工具会自动分析项目结构，无需手动更新。当项目结构发生变化时，只需重新运行相应的脚本即可生成最新的可视化结果。

所有工具都设计为：
- 忽略 `__pycache__`、`.venv`、`.git` 等目录
- 自动处理编码问题
- 生成独立的HTML文件（无需外部服务器）
- 支持大型项目（自动限制输出大小）
