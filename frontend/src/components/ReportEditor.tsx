// 报告编辑器组件
// frontend/src/components/ReportEditor.tsx

import React, { useState, useCallback } from 'react';
import MDEditor from '@uiw/react-md-editor';
import { Button, Input, Modal, message, Space, Tag, Select } from 'antd';
import {
  DownloadOutlined,
  SaveOutlined,
  EditOutlined,
  EyeOutlined,
  FileMarkdownOutlined,
  FileTextOutlined,
  FilePdfOutlined
} from '@ant-design/icons';

interface ReportSection {
  id: string;
  title: string;
  content: string;
  order: number;
  level: number;
}

interface ReportMetadata {
  title: string;
  author: string;
  date: string;
  version: string;
  tags: string[];
  description: string;
}

interface Report {
  id: string;
  metadata: ReportMetadata;
  sections: ReportSection[];
  template: string;
  created_at: string;
  updated_at: string;
}

interface ReportEditorProps {
  initialContent?: string;
  initialTitle?: string;
  onSave?: (report: Report) => void;
  onExport?: (reportId: string, format: string) => void;
}

export const ReportEditor: React.FC<ReportEditorProps> = ({
  initialContent = '',
  initialTitle = '新建报告',
  onSave,
  onExport,
}) => {
  const [report, setReport] = useState<Report | null>(null);
  const [editMode, setEditMode] = useState(true);
  const [title, setTitle] = useState(initialTitle);
  const [author, setAuthor] = useState('');
  const [template, setTemplate] = useState('standard');
  const [content, setContent] = useState(initialContent);
  const [loading, setLoading] = useState(false);
  const [exportModalVisible, setExportModalVisible] = useState(false);

  // 创建报告
  const handleCreateReport = useCallback(async () => {
    if (!title.trim()) {
      message.error('请输入报告标题');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/reports/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          content,
          author,
          template,
          auto_structure: true,
        }),
      });

      if (!response.ok) throw new Error('创建报告失败');

      const newReport = await response.json();
      setReport(newReport);
      message.success('报告创建成功');

      if (onSave) onSave(newReport);
    } catch (error) {
      console.error('创建报告失败:', error);
      message.error('创建报告失败');
    } finally {
      setLoading(false);
    }
  }, [title, content, author, template, onSave]);

  // 更新报告
  const handleUpdateReport = useCallback(async () => {
    if (!report) {
      message.error('请先创建报告');
      return;
    }

    setLoading(true);
    try {
      // 从内容重新生成sections
      const sections = parseContentToSections(content);

      const response = await fetch(`/api/reports/${report.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          metadata: {
            ...report.metadata,
            title,
            author,
          },
          sections,
        }),
      });

      if (!response.ok) throw new Error('更新报告失败');

      const updatedReport = await response.json();
      setReport(updatedReport);
      message.success('报告已保存');

      if (onSave) onSave(updatedReport);
    } catch (error) {
      console.error('更新报告失败:', error);
      message.error('更新报告失败');
    } finally {
      setLoading(false);
    }
  }, [report, title, content, author, onSave]);

  // 导出报告
  const handleExport = useCallback(async (format: string) => {
    if (!report) {
      message.error('请先创建报告');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/reports/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_id: report.id,
          format,
          include_toc: true,
          include_metadata: true,
        }),
      });

      if (!response.ok) throw new Error('导出失败');

      // 下载文件
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title}.${format === 'markdown' ? 'md' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      message.success('导出成功');
      setExportModalVisible(false);

      if (onExport) onExport(report.id, format);
    } catch (error) {
      console.error('导出失败:', error);
      message.error('导出失败');
    } finally {
      setLoading(false);
    }
  }, [report, title, onExport]);

  // 解析内容为章节
  const parseContentToSections = (text: string): ReportSection[] => {
    const sections: ReportSection[] = [];
    const lines = text.split('\n');

    let currentSection: any = null;
    let order = 0;

    lines.forEach((line) => {
      const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);

      if (headingMatch) {
        if (currentSection && currentSection.content) {
          sections.push({
            id: `section-${order}`,
            title: currentSection.title,
            content: currentSection.content.trim(),
            order,
            level: currentSection.level,
          });
          order++;
        }

        currentSection = {
          title: headingMatch[2],
          content: '',
          level: headingMatch[1].length,
        };
      } else if (currentSection) {
        currentSection.content += line + '\n';
      }
    });

    if (currentSection && currentSection.content) {
      sections.push({
        id: `section-${order}`,
        title: currentSection.title,
        content: currentSection.content.trim(),
        order,
        level: currentSection.level,
      });
    }

    return sections;
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* 工具栏 */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Input
            placeholder="报告标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ width: '300px' }}
            size="large"
          />
          <Input
            placeholder="作者（可选）"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            style={{ width: '150px' }}
          />
          <Select
            value={template}
            onChange={setTemplate}
            style={{ width: '120px' }}
            options={[
              { label: '标准', value: 'standard' },
              { label: '技术', value: 'technical' },
              { label: '高管', value: 'executive' },
              { label: '安全', value: 'security' },
            ]}
          />
        </Space>

        <Space>
          <Button
            icon={editMode ? <EyeOutlined /> : <EditOutlined />}
            onClick={() => setEditMode(!editMode)}
          >
            {editMode ? '预览' : '编辑'}
          </Button>

          {report ? (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleUpdateReport}
              loading={loading}
            >
              保存
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleCreateReport}
              loading={loading}
            >
              创建报告
            </Button>
          )}

          <Button
            icon={<DownloadOutlined />}
            onClick={() => setExportModalVisible(true)}
            disabled={!report}
          >
            导出
          </Button>
        </Space>
      </div>

      {/* 报告信息 */}
      {report && (
        <div style={{ marginBottom: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '4px' }}>
          <Space>
            <Tag color="blue">报告ID: {report.id}</Tag>
            <Tag color="green">创建: {new Date(report.created_at).toLocaleString()}</Tag>
            <Tag color="orange">更新: {new Date(report.updated_at).toLocaleString()}</Tag>
          </Space>
        </div>
      )}

      {/* Markdown编辑器 */}
      <div data-color-mode="light">
        <MDEditor
          value={content}
          onChange={(val?: string) => setContent(val || '')}
          preview={editMode ? 'live' : 'preview'}
          height={600}
          visibleDragbar={false}
        />
      </div>

      {/* 导出模态框 */}
      <Modal
        title="导出报告"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={null}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Button
            block
            size="large"
            icon={<FileMarkdownOutlined />}
            onClick={() => handleExport('markdown')}
            loading={loading}
          >
            导出为 Markdown (.md)
          </Button>

          <Button
            block
            size="large"
            icon={<FileTextOutlined />}
            onClick={() => handleExport('html')}
            loading={loading}
          >
            导出为 HTML (.html)
          </Button>

          <Button
            block
            size="large"
            icon={<FilePdfOutlined />}
            disabled
            title="需要安装Pandoc"
          >
            导出为 PDF (.pdf) - 即将推出
          </Button>
        </Space>
      </Modal>

      {/* 使用提示 */}
      <div style={{ marginTop: '24px', padding: '16px', background: '#e6f7ff', border: '1px solid #91d5ff', borderRadius: '4px' }}>
        <h4>使用提示：</h4>
        <ul>
          <li>使用 Markdown 语法编写报告（支持标题、列表、表格、代码等）</li>
          <li>标题会自动识别为章节（使用 #, ##, ### 等）</li>
          <li>点击"创建报告"保存第一个版本，之后使用"保存"更新</li>
          <li>点击"导出"可下载 Markdown 或 HTML 格式</li>
          <li>报告会自动生成目录和元数据</li>
        </ul>
      </div>
    </div>
  );
};

export default ReportEditor;
