import type { AdminUserSummary } from "@/types/api";
import { request, authFetch, parseOrThrow } from "./api-client";

export const adminUserApi = {
  adminUsers() {
    return request<AdminUserSummary[]>("/admin/users");
  },
  async adminUpdateRole(userId: string, role: string) {
    const res = await authFetch(`/admin/users/${encodeURIComponent(userId)}/role`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    return parseOrThrow<AdminUserSummary>(res);
  },
  async adminUpdateStatus(userId: string, statusValue: string) {
    const res = await authFetch(`/admin/users/${encodeURIComponent(userId)}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: statusValue }),
    });
    return parseOrThrow<AdminUserSummary>(res);
  },
  async adminUpdateClassification(
    userId: string,
    input: { businessUnit?: string; department?: string; userType?: string; dataScope?: string },
  ) {
    const res = await authFetch(`/admin/users/${encodeURIComponent(userId)}/classification`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        business_unit: input.businessUnit || null,
        department: input.department || null,
        user_type: input.userType || null,
        data_scope: input.dataScope || null,
      }),
    });
    return parseOrThrow<AdminUserSummary>(res);
  },
  async adminCreateAdmin(input: {
    username: string;
    password: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newAdminApprovalToken: string;
  }) {
    const res = await authFetch("/admin/users/create-admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: input.username,
        password: input.password,
        approval_token: input.approvalToken,
        ticket_id: input.ticketId,
        reason: input.reason,
        new_admin_approval_token: input.newAdminApprovalToken,
      }),
    });
    return parseOrThrow<AdminUserSummary>(res);
  },
  async adminResetApprovalToken(input: {
    userId: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newAdminApprovalToken: string;
  }) {
    const res = await authFetch(`/admin/users/${encodeURIComponent(input.userId)}/reset-approval-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approval_token: input.approvalToken,
        ticket_id: input.ticketId,
        reason: input.reason,
        new_admin_approval_token: input.newAdminApprovalToken,
      }),
    });
    return parseOrThrow<AdminUserSummary>(res);
  },
  async adminResetPassword(input: {
    userId: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newPassword: string;
  }) {
    const res = await authFetch(`/admin/users/${encodeURIComponent(input.userId)}/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approval_token: input.approvalToken,
        ticket_id: input.ticketId,
        reason: input.reason,
        new_password: input.newPassword,
      }),
    });
    return parseOrThrow<AdminUserSummary>(res);
  },
};
