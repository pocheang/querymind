import { useEffect, useState } from 'react';
import '../styles/components/keyboard-help.css';

interface Shortcut {
  keys: string[];
  description: string;
  category: string;
}

const shortcuts: Shortcut[] = [
  // 消息操作
  { keys: ['Ctrl', 'Enter'], description: '发送消息', category: '消息操作' },
  { keys: ['Shift', 'Enter'], description: '换行', category: '消息操作' },
  { keys: ['Esc'], description: '清空输入框', category: '消息操作' },

  // 导航
  { keys: ['Ctrl', 'K'], description: '聚焦到搜索框', category: '导航' },
  { keys: ['Ctrl', 'N'], description: '新建会话', category: '导航' },
  { keys: ['Ctrl', 'B'], description: '切换侧边栏', category: '导航' },

  // 选项切换
  { keys: ['Ctrl', 'W'], description: '切换联网检索', category: '选项' },
  { keys: ['Ctrl', 'R'], description: '切换推理增强', category: '选项' },

  // 其他
  { keys: ['?'], description: '显示快捷键帮助', category: '其他' },
  { keys: ['Ctrl', '/'], description: '显示快捷键帮助', category: '其他' },
];

export function KeyboardHelp() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 按 ? 或 Ctrl+/ 打开帮助
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
        // 确保不在输入框中
        const target = e.target as HTMLElement;
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault();
          setIsOpen(true);
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        setIsOpen(true);
      }

      // 按 Esc 关闭帮助
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  // 按类别分组
  const groupedShortcuts = shortcuts.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = [];
    }
    acc[shortcut.category].push(shortcut);
    return acc;
  }, {} as Record<string, Shortcut[]>);

  return (
    <>
      <div
        className="keyboard-help-backdrop"
        onClick={() => setIsOpen(false)}
        aria-hidden="true"
      />
      <div
        className="keyboard-help-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-help-title"
      >
        <div className="keyboard-help-header">
          <h2 id="keyboard-help-title">键盘快捷键</h2>
          <button
            type="button"
            className="keyboard-help-close"
            onClick={() => setIsOpen(false)}
            aria-label="关闭快捷键帮助"
          >
            ×
          </button>
        </div>

        <div className="keyboard-help-content">
          {Object.entries(groupedShortcuts).map(([category, items]) => (
            <div key={category} className="keyboard-help-section">
              <h3 className="keyboard-help-category">{category}</h3>
              <div className="keyboard-help-list">
                {items.map((shortcut, index) => (
                  <div key={index} className="keyboard-help-item">
                    <div className="keyboard-help-keys">
                      {shortcut.keys.map((key, i) => (
                        <span key={i}>
                          <kbd className="keyboard-key">{key}</kbd>
                          {i < shortcut.keys.length - 1 && (
                            <span className="keyboard-plus">+</span>
                          )}
                        </span>
                      ))}
                    </div>
                    <span className="keyboard-help-description">
                      {shortcut.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="keyboard-help-footer">
          <p className="keyboard-help-hint">
            按 <kbd className="keyboard-key">Esc</kbd> 或点击外部区域关闭
          </p>
        </div>
      </div>
    </>
  );
}
