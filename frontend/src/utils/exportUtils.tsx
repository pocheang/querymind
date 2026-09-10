// 数据导出工具函数
export function exportToCSV(data: Array<Record<string, unknown>>, filename: string) {
  if (data.length === 0) return;

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        // Skip complex objects and arrays
        if (value && typeof value === 'object') {
          return JSON.stringify(value);
        }
        // 转义包含逗号或引号的值
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      }).join(',')
    )
  ].join('\n');

  downloadFile(csvContent, filename, 'text/csv;charset=utf-8;');
}

export function exportToJSON(data: Array<Record<string, unknown>>, filename: string) {
  const jsonContent = JSON.stringify(data, null, 2);
  downloadFile(jsonContent, filename, 'application/json');
}

export function exportTableToExcel(tableId: string, filename: string) {
  // 简化版Excel导出（使用HTML table）
  const table = document.getElementById(tableId);
  if (!table) return;

  const html = table.outerHTML;
  const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.xls`;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// React组件：导出按钮
import { useTranslation } from "react-i18next";
import { FileJson, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ExportButtonsProps {
  data: Array<Record<string, unknown>>;
  filename: string;
  onExport?: () => void;
}

export function ExportButtons({ data, filename, onExport }: Readonly<ExportButtonsProps>) {
  const { t } = useTranslation();

  const handleExportCSV = () => {
    exportToCSV(data, `${filename}.csv`);
    onExport?.();
  };

  const handleExportJSON = () => {
    exportToJSON(data, `${filename}.json`);
    onExport?.();
  };

  return (
    /* `secondary tiny-btn` until 2026-09-07, which is a stylesheet that was
       deleted with the button sheets -- so both buttons had been rendering as
       bare text beside every export-capable dashboard. */
    <div className="flex gap-2">
      <Button variant="secondary" size="xs" onClick={handleExportCSV} title={t("admin.export.csv", "Export as CSV")}>
        <FileSpreadsheet className="size-3.5" aria-hidden="true" />
        CSV
      </Button>
      <Button
        variant="secondary"
        size="xs"
        onClick={handleExportJSON}
        title={t("admin.export.json", "Export as JSON")}
      >
        <FileJson className="size-3.5" aria-hidden="true" />
        JSON
      </Button>
    </div>
  );
}
