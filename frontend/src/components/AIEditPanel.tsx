// AI辅助编辑功能 - 前端组件
// frontend/src/components/AIEditPanel.tsx

import React, { useState } from 'react';
import { Button, Modal, Radio, Input, Space, message, Spin } from 'antd';
import {
  ThunderboltOutlined,
  ExpandOutlined,
  CompressOutlined,
  EditOutlined,
  TranslationOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const { TextArea } = Input;

interface AIEditPanelProps {
  content: string;
  onEditComplete: (editedContent: string) => void;
  language?: string;
}

type Operation = 'polish' | 'expand' | 'summarize' | 'rewrite' | 'translate' | 'custom';

export const AIEditPanel: React.FC<AIEditPanelProps> = ({
  content,
  onEditComplete,
  language = 'zh',
}) => {
  const [modalVisible, setModalVisible] = useState(false);
  const [operation, setOperation] = useState<Operation>('polish');
  const [style, setStyle] = useState('professional');
  const [customInstruction, setCustomInstruction] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  // 操作选项
  const operations = [
    { label: '✨ 润色', value: 'polish', icon: <ThunderboltOutlined />, desc: '改进语言表达' },
    { label: '📈 扩展', value: 'expand', icon: <ExpandOutlined />, desc: '增加细节和深度' },
    { label: '📝 总结', value: 'summarize', icon: <CompressOutlined />, desc: '提炼核心要点' },
    { label: '🔄 重写', value: 'rewrite', icon: <EditOutlined />, desc: '按指定风格重写' },
    { label: '🌐 翻译', value: 'translate', icon: <TranslationOutlined />, desc: '翻译为其他语言' },
    { label: '🎯 自定义', value: 'custom', icon: <CheckCircleOutlined />, desc: '自定义编辑要求' },
  ];

  // 风格选项
  const styles = [
    { label: '专业', value: 'professional' },
    { label: '技术', value: 'technical' },
    { label: '高管', value: 'executive' },
    { label: '随意', value: 'casual' },
  ];

  // 执行AI编辑
  const handleAIEdit = async () => {
    if (operation === 'custom' && !customInstruction.trim()) {
      message.error('请输入自定义指令');
      return;
    }

    setLoading(true);
    setShowPreview(false);

    try {
      const response = await fetch('/api/reports/ai-edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation,
          content,
          instruction: customInstruction,
          style,
          language,
        }),
      });

      if (!response.ok) throw new Error('AI编辑失败');

      const result = await response.json();
      setPreviewContent(result.edited);
      setShowPreview(true);

      message.success(`${result.changes_summary}`);
    } catch (error) {
      console.error('AI编辑失败:', error);
      message.error('AI编辑失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 应用编辑
  const handleApply = () => {
    onEditComplete(previewContent);
    setModalVisible(false);
    setShowPreview(false);
    message.success('已应用AI编辑');
  };

  // 取消编辑
  const handleCancel = () => {
    setModalVisible(false);
    setShowPreview(false);
    setPreviewContent('');
  };

  return (
    <>
      <Button
        icon={<ThunderboltOutlined />}
        onClick={() => setModalVisible(true)}
        type="dashed"
      >
        AI辅助编辑
      </Button>

      <Modal
        title="AI辅助编辑"
        open={modalVisible}
        onCancel={handleCancel}
        width={800}
        footer={null}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 操作选择 */}
          <div>
            <div style={{ marginBottom: '8px', fontWeight: 500 }}>选择编辑操作：</div>
            <Radio.Group
              value={operation}
              onChange={(e) => setOperation(e.target.value)}
              style={{ width: '100%' }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {operations.map((op) => (
                  <Radio key={op.value} value={op.value} style={{ width: '100%' }}>
                    <Space>
                      {op.icon}
                      <span>
                        <strong>{op.label}</strong>
                        <span style={{ color: '#999', marginLeft: '8px' }}>
                          {op.desc}
                        </span>
                      </span>
                    </Space>
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
          </div>

          {/* 重写风格选择 */}
          {operation === 'rewrite' && (
            <div>
              <div style={{ marginBottom: '8px', fontWeight: 500 }}>选择风格：</div>
              <Radio.Group value={style} onChange={(e) => setStyle(e.target.value)}>
                {styles.map((s) => (
                  <Radio.Button key={s.value} value={s.value}>
                    {s.label}
                  </Radio.Button>
                ))}
              </Radio.Group>
            </div>
          )}

          {/* 自定义指令 */}
          {operation === 'custom' && (
            <div>
              <div style={{ marginBottom: '8px', fontWeight: 500 }}>输入编辑要求：</div>
              <TextArea
                placeholder="例如：添加3个具体的实施步骤、把这段改得更简洁、增加数据支撑等"
                value={customInstruction}
                onChange={(e) => setCustomInstruction(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {/* 原始内容预览 */}
          <div>
            <div style={{ marginBottom: '8px', fontWeight: 500 }}>原始内容：</div>
            <div
              style={{
                padding: '12px',
                background: '#f5f5f5',
                borderRadius: '4px',
                maxHeight: '150px',
                overflow: 'auto',
              }}
            >
              {content.substring(0, 300)}
              {content.length > 300 && '...'}
            </div>
          </div>

          {/* AI编辑结果预览 */}
          {showPreview && (
            <div>
              <div style={{ marginBottom: '8px', fontWeight: 500 }}>AI编辑结果：</div>
              <div
                style={{
                  padding: '12px',
                  background: '#e6f7ff',
                  border: '1px solid #91d5ff',
                  borderRadius: '4px',
                  maxHeight: '300px',
                  overflow: 'auto',
                }}
              >
                {previewContent}
              </div>
            </div>
          )}

          {/* 操作按钮 */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            {!showPreview ? (
              <>
                <Button onClick={handleCancel}>取消</Button>
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={handleAIEdit}
                  loading={loading}
                >
                  开始AI编辑
                </Button>
              </>
            ) : (
              <>
                <Button onClick={handleCancel}>放弃</Button>
                <Button onClick={() => setShowPreview(false)}>重新编辑</Button>
                <Button type="primary" onClick={handleApply}>
                  应用此编辑
                </Button>
              </>
            )}
          </div>

          {/* 加载提示 */}
          {loading && (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <Spin tip="AI正在编辑中，请稍候..." />
            </div>
          )}
        </Space>
      </Modal>
    </>
  );
};

export default AIEditPanel;
