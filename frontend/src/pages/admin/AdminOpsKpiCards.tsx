import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
};

export function AdminOpsKpiCards({ ops }: Props) {
  return (
    <>
      <div className="ops-kpi-grid ops-kpi-grid-primary">
        <div className="ops-kpi-card">
          <span>请求总数</span>
          <strong>{ops.kpi.requests_total}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>成功请求</span>
          <strong>{ops.kpi.requests_success}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>失败请求</span>
          <strong>{ops.kpi.requests_error}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>错误率</span>
          <strong>{ops.kpi.error_rate_percent}%</strong>
        </div>
        <div className="ops-kpi-card">
          <span>活跃会话</span>
          <strong>{ops.kpi.active_sessions}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>活跃用户</span>
          <strong>{ops.kpi.active_users}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>问答请求</span>
          <strong>{ops.kpi.queries}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>上传次数</span>
          <strong>{ops.kpi.uploads}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>登录成功</span>
          <strong>{ops.kpi.login_success}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>登录失败</span>
          <strong>{ops.kpi.login_failed}</strong>
        </div>
      </div>
      <div className="ops-kpi-grid ops-kpi-grid-secondary">
        <div className="ops-kpi-card">
          <span>用户总数</span>
          <strong>{ops.users.total}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>启用用户</span>
          <strong>{ops.users.active}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>禁用用户</span>
          <strong>{ops.users.disabled}</strong>
        </div>
        <div className="ops-kpi-card">
          <span>管理员数量</span>
          <strong>{ops.users.admin}</strong>
        </div>
      </div>
    </>
  );
}
