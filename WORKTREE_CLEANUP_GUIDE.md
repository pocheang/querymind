# Worktree 清理指南

**日期**: 2026-06-08  
**状态**: 需要手动执行

---

## 📊 当前状态

### Worktrees 分析
| Worktree | 状态 | 大小 | 操作 |
|---------|------|------|------|
| advanced-rag-techniques | ✅ 已合并到main | 6.0MB | 🗑️ 可以删除 |
| chinese-nlp-optimization | ✅ 已合并，修改已保存 | 6.2MB | 🗑️ 可以删除 |
| agent-execution-visualization | ❌ 未合并 | 5.2MB | ⚠️ 保留 |

### Stash 备份
✅ 已保存 chinese-nlp-optimization 的未提交修改：
```
stash@{0}: On worktree-chinese-nlp-optimization: 保存未提交的中文NLP优化修改 - 2026-06-08
```

**恢复修改的命令**:
```bash
git stash apply stash@{0}
```

---

## 🛠️ 手动清理步骤

### 步骤 1: 删除 worktree 目录

在项目根目录执行：

```powershell
# 方法1: 使用 git worktree remove（推荐）
git worktree remove .claude/worktrees/advanced-rag-techniques
git worktree remove .claude/worktrees/chinese-nlp-optimization

# 如果上面命令失败，使用方法2
# 方法2: 手动删除目录
Remove-Item -Recurse -Force ".claude\worktrees\advanced-rag-techniques"
Remove-Item -Recurse -Force ".claude\worktrees\chinese-nlp-optimization"

# 然后清理 git 引用
git worktree prune
```

### 步骤 2: 删除本地分支（可选）

```powershell
# 删除已合并的分支
git branch -d worktree-advanced-rag-techniques
git branch -d worktree-chinese-nlp-optimization
```

### 步骤 3: 验证清理结果

```powershell
# 查看剩余的 worktrees
git worktree list

# 应该只剩下：
# C:/Users/pocheang/Desktop/llm/multi_agent_rag_local_v4 [main]
# C:/Users/pocheang/Desktop/llm/multi_agent_rag_local_v4/.claude/worktrees/agent-execution-visualization [...]

# 查看磁盘空间释放
Get-ChildItem .claude\worktrees | Measure-Object -Property Length -Sum
```

### 步骤 4: 清理远程分支（可选）

如果这些分支已推送到远程仓库，可以选择删除：

```powershell
# 删除远程分支（谨慎操作！）
git push origin --delete worktree-advanced-rag-techniques
git push origin --delete worktree-chinese-nlp-optimization

# 清理本地的远程分支引用
git fetch --prune
```

---

## 📝 关于 agent-execution-visualization

这个 worktree **暂时保留**，因为：
- ❌ 还未合并到 main 分支
- 📁 有相关文档存在于 `docs/features/agents/agent_execution_tracking.md`
- 💡 可能还包含未合并的代码更改

### 检查是否需要保留

```powershell
# 查看该分支与 main 的差异
git log main..worktree-agent-execution-visualization --oneline

# 查看未合并的更改
git diff main...worktree-agent-execution-visualization
```

如果确认不需要，可以用相同方法删除。

---

## 🔄 恢复已保存的修改

如果需要恢复 chinese-nlp-optimization 中的修改：

```powershell
# 查看 stash 内容
git stash show stash@{0} -p

# 应用修改（保留 stash）
git stash apply stash@{0}

# 或应用并删除 stash
git stash pop stash@{0}
```

修改内容：
- `app/services/chinese_tokenizer.py`: 添加了默认 POS 标签处理
- `tests/unit/test_chinese_document_indexer.py`: 相关测试更新

---

## 📊 预期结果

### 清理前
```
.claude/worktrees/
├── advanced-rag-techniques/      (6.0MB)
├── agent-execution-visualization/ (5.2MB)
└── chinese-nlp-optimization/      (6.2MB)
总计: ~17.4MB
```

### 清理后
```
.claude/worktrees/
└── agent-execution-visualization/ (5.2MB)
总计: ~5.2MB

释放空间: ~12.2MB
```

---

## ⚠️ 注意事项

1. **删除前确认**: 确保所有重要更改已提交或保存到 stash
2. **远程分支**: 删除远程分支前与团队确认
3. **备份**: 如有疑虑，先备份整个 worktrees 目录
4. **恢复**: 如果误删，可以用 `git worktree add` 重新创建

---

## 📞 相关文档

- [Claude 文件夹维护指南](docs/project/CLAUDE_FOLDER_CLEANUP_GUIDE.md)
- [项目维护建议](docs/project/MAINTENANCE_RECOMMENDATIONS.md)

---

**创建时间**: 2026-06-08  
**下次审查**: 建议每季度检查一次 worktrees 状态
