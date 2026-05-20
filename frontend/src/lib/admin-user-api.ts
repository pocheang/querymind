import type { AdminUserSummary } from "@/types/api";
import { request } from "./api-client";
import { buildPatchRequest, buildPostRequest, encodePathParam } from "./api-helpers";

export const adminUserApi = {
  adminUsers() {
    return request<AdminUserSummary[]>("/admin/users");
  },
  adminUpdateRole(userId: string, role: string) {
    return buildPatchRequest<AdminUserSummary>(`/admin/users/${encodePathParam(userId)}/role`, { role });
  },
  adminUpdateStatus(userId: string, statusValue: string) {
    return buildPatchRequest<AdminUserSummary>(`/admin/users/${encodePathParam(userId)}/status`, { status: statusValue });
  },
  adminUpdateClassification(
    userId: string,
    input: { businessUnit?: string; department?: string; userType?: string; dataScope?: string },
  ) {
    return buildPatchRequest<AdminUserSummary>(`/admin/users/${encodePathParam(userId)}/classification`, {
      business_unit: input.businessUnit || null,
      department: input.department || null,
      user_type: input.userType || null,
      data_scope: input.dataScope || null,
    });
  },
  adminCreateAdmin(input: {
    username: string;
    password: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newAdminApprovalToken: string;
  }) {
    return buildPostRequest<AdminUserSummary>("/admin/users/create-admin", {
      username: input.username,
      password: input.password,
      approval_token: input.approvalToken,
      ticket_id: input.ticketId,
      reason: input.reason,
      new_admin_approval_token: input.newAdminApprovalToken,
    });
  },
  adminResetApprovalToken(input: {
    userId: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newAdminApprovalToken: string;
  }) {
    return buildPostRequest<AdminUserSummary>(`/admin/users/${encodePathParam(input.userId)}/reset-approval-token`, {
      approval_token: input.approvalToken,
      ticket_id: input.ticketId,
      reason: input.reason,
      new_admin_approval_token: input.newAdminApprovalToken,
    });
  },
  adminResetPassword(input: {
    userId: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newPassword: string;
  }) {
    return buildPostRequest<AdminUserSummary>(`/admin/users/${encodePathParam(input.userId)}/reset-password`, {
      approval_token: input.approvalToken,
      ticket_id: input.ticketId,
      reason: input.reason,
      new_password: input.newPassword,
    });
  },
};
