---
name: gradual-refactoring-policy
description: Policy for gradually refactoring long files during future modifications
metadata:
  type: project
  created: 2026-06-03
  priority: high
---

# Gradual Refactoring Policy

**Principle**: 渐进式重构，不急于一次性改完所有代码

**Last Updated**: 2026-06-03

---

## 🎯 核心原则

### "Boy Scout Rule" (童子军规则)
> **"让营地比你来时更干净"**
> 
> 每次修改代码时，让它比修改前更好一点。

**不是**: 看到长文件就全部重构  
**而是**: 修改某个文件时，顺便重构相关部分

---

## 📋 渐进式重构策略

### 1. **新代码严格遵守标准**
```
✅ 所有新文件:
   - 必须 < 500行
   - 单一职责
   - 有完整文档
   - 有测试覆盖

✅ 新功能/模块:
   - 从一开始就设计好结构
   - 不要等到长了再拆分
```

### 2. **修改现有代码时逐步重构**
```
当你需要修改一个长文件时:

1. 先完成功能修改 (主要任务)
   ↓
2. 评估是否可以顺便重构
   ↓
3. 如果时间允许，重构相关部分
   ↓
4. 记录重构改进

不强制在每次修改时都重构，但鼓励顺便改进。
```

### 3. **重构时机判断**

#### ✅ **好的重构时机**:
- 需要修改某个长文件 (>500行)
- 修改涉及的函数 >50行
- 发现重复代码
- 添加新功能到现有模块
- 修复bug时发现代码混乱
- 有充足时间
- 不影响主要任务交付

#### ❌ **暂缓重构的情况**:
- 紧急bug修复（先修复，后重构）
- 时间紧迫的功能交付
- 代码虽长但逻辑清晰且稳定
- 重构风险高（核心功能，测试覆盖不足）
- 用户正在等待功能

---

## 🔧 实际操作指南

### 场景1: 修改现有长文件的某个函数

```python
# 例如: app/services/some_long_service.py (800行)

# 步骤:
1. 完成你需要修改的功能
2. 如果这个函数很长 (>50行)，考虑提取辅助函数
3. 如果这个功能相对独立，考虑提取到新文件
4. 更新相关导入和测试

# 示例:
修改前: some_long_service.py (800行)
修改后:
  ├── some_long_service.py (700行) ← 减少了100行
  └── extracted_helper.py (120行) ← 新文件，职责单一
```

### 场景2: 添加新功能到现有模块

```python
# 例如: 需要在 retrievers/ 添加新的检索方法

# ❌ 错误做法:
# 直接添加到 hybrid_retriever.py (已经500行)
# → 文件变成600行

# ✅ 正确做法:
# 创建新文件 advanced_retriever.py (200行)
# 保持 hybrid_retriever.py 不变
```

### 场景3: 发现代码重复

```python
# 在修改过程中发现3个地方有相同逻辑

# 重构步骤:
1. 提取共享函数到 utils/ 或 helpers/
2. 更新所有调用点
3. 添加测试确保行为一致
4. 记录在commit message: "refactor: extract common logic"
```

---

## 📝 重构记录规范

### Git Commit Message

```bash
# 功能修改 + 顺便重构
git commit -m "feat: add new feature X

- Implement feature X
- Refactor: extract helper function to reduce file length
- Reduce some_service.py from 800 to 650 lines"

# 纯重构 (少见，通常和功能修改一起)
git commit -m "refactor: split large service into modules

- Extract retrieval logic to retrieval_service.py
- Extract reranking logic to reranking_service.py
- Main service reduced from 800 to 300 lines"
```

### 可选: 重构日志

如果重构比较大，可以简单记录：

```markdown
# .claude/completed/YYYY-MM-DD-refactoring-notes.md

## File: app/services/some_service.py
- Before: 800 lines
- After: Split into 3 files (300 + 250 + 220)
- Reason: Adding feature X, noticed file too long
- Benefits: Easier to test, clearer responsibilities
```

---

## 🎯 优先级指南

### 高优先级（应该重构）
- 文件 > 800行 且需要修改
- 函数 > 100行 且需要修改
- 明显的重复代码（3+处）
- 测试困难的代码
- 经常需要修改的热点文件

### 中优先级（可以重构）
- 文件 500-800行 且需要修改
- 函数 50-100行 且需要修改
- 职责不够单一但还能接受
- 有时间余量的情况

### 低优先级（暂不重构）
- 文件虽长但逻辑清晰且稳定
- 不经常修改的代码
- 测试覆盖完善且运行良好
- 没有导致实际问题

---

## 📊 重构示例

### 示例1: 渐进式拆分大文件

```python
# Original: app/agents/rag_agent.py (1200 lines)

# 第一次修改 (添加新检索方法):
# → 提取检索逻辑到 retrieval_logic.py (300行)
# → rag_agent.py 减少到 900行

# 第二次修改 (优化重排序):
# → 提取重排逻辑到 reranking_logic.py (250行)
# → rag_agent.py 减少到 650行

# 第三次修改 (添加缓存):
# → 提取缓存逻辑到 cache_manager.py (200行)
# → rag_agent.py 减少到 450行 ✅

# 三次修改后:
agents/
├── rag_agent.py           # 450行 - 核心编排
├── retrieval_logic.py     # 300行 - 检索
├── reranking_logic.py     # 250行 - 重排
└── cache_manager.py       # 200行 - 缓存
```

### 示例2: 边修改边改进

```python
# 任务: 修复 hybrid_retriever.py 的一个bug

# 修改过程中发现:
# - 某个函数有80行（太长）
# - 有重复的参数验证逻辑

# 顺便改进:
1. 修复原bug
2. 将80行函数拆分成3个小函数
3. 提取共享的验证逻辑到 _validate_params()

# 结果:
# - Bug修复 ✅
# - 代码更清晰 ✅
# - 文件从520行减少到480行 ✅
```

---

## ⚠️ 重构注意事项

### DO (应该做)
- ✅ 保持原有功能不变
- ✅ 先写测试再重构（或确认现有测试通过）
- ✅ 小步快跑，每次改进一点
- ✅ 重构后运行完整测试
- ✅ 更新相关文档
- ✅ 保持commits清晰

### DON'T (不要做)
- ❌ 大范围重构没有测试覆盖的代码
- ❌ 在紧急修复时进行大规模重构
- ❌ 改变功能行为（重构应该保持行为不变）
- ❌ 一次性重构所有长文件（风险太大）
- ❌ 为了重构而重构（要有实际收益）

---

## 📈 长期效果

### 预期改进时间线

```
现在 (2026-06):
  - 新代码: 100% 符合标准
  - 现有代码: 有些文件 >500行（历史遗留）

3个月后 (2026-09):
  - 经常修改的热点文件: 大部分已优化
  - 稳定的旧代码: 可能还是长文件（但不影响）

6个月后 (2026-12):
  - 项目整体: 80%+ 代码符合标准
  - 代码库: 更易维护

1年后 (2027-06):
  - 基本所有活跃代码: 符合标准
  - 遗留的长文件: 仅限极少数稳定模块
```

---

## 🎓 团队沟通

### 对其他开发者的说明

```markdown
# 重构指南 for 团队

我们采用**渐进式重构**策略:

1. 所有新代码必须符合标准（<500行）
2. 修改现有代码时，如果方便，顺便重构相关部分
3. 不强制一次性重构所有旧代码
4. 重构时保持功能不变，确保测试通过

原则: "让代码比你来时更好"

如果你发现某个文件特别难维护，可以在修改时考虑拆分。
如果时间紧迫，可以先完成功能，后续再重构。
```

---

## 📋 检查清单

### 修改现有代码时

```
□ 完成主要功能修改
□ 运行测试确认功能正常
□ 评估: 这个文件是否 >500行？
□ 评估: 修改的函数是否 >50行？
□ 评估: 是否有明显的改进空间？
□ 评估: 是否有时间进行小幅重构？
□ 如果答案是"是"，考虑小规模重构
□ 重构后重新运行测试
□ 更新文档（如果需要）
□ 提交时说明重构改进
```

---

## 🎯 总结

**核心思想**: 
- ✅ 新代码: 严格标准
- 🔄 旧代码: 渐进改善
- 🎯 目标: 长期改进，不急于一时

**记住**:
> "Perfect is the enemy of good"
> 
> 不要追求一次性完美，而要持续改进。

**实践**:
- 每次修改让代码更好一点
- 积少成多，最终整体改善
- 平衡重构和功能交付

---

Related: [[project-workflow-and-standards]]
