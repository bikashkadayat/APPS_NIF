import api from './api';
import { unwrapPaginated } from './utils';

const leaveTypeMap = {
  'Annual Leave': 'annual',
  'Sick Leave': 'sick',
  'Casual Leave': 'casual',
  'Maternity Leave': 'maternity',
  'Paternity Leave': 'paternity',
  'Compensatory Leave': 'compensatory',
};

const apiToUiType = {
  annual: 'Annual Leave',
  sick: 'Sick Leave',
  casual: 'Casual Leave',
  maternity: 'Maternity Leave',
  paternity: 'Paternity Leave',
  compensatory: 'Compensatory Leave',
};

// UI label for a backend leave-type code (used to build category-limited menus).
export const leaveTypeLabel = (code) => apiToUiType[code] || code;

const calculateDays = (start, end) => {
  const d1 = new Date(start);
  const d2 = new Date(end);
  const diff = Math.abs(d2 - d1);
  return Math.ceil(diff / (1000 * 60 * 60 * 24)) + 1;
};

const mapLeave = (leave) => ({
  id: leave.id,
  userId: leave.user,               // owner id — for robust self-filtering
  employee: leave.user_name || 'Unknown',
  type: apiToUiType[leave.leave_type] || leave.leave_type || 'Annual Leave',
  start: leave.start_date,
  end: leave.end_date,
  days: calculateDays(leave.start_date, leave.end_date),
  reason: leave.reason || '',
  handover_notes: leave.handover_notes || '',
  status: leave.status,
  manager: leave.approver_name || 'Unassigned',
  applied: leave.created_at ? leave.created_at.split('T')[0] : '',
});

const toBackendPayload = (data) => ({
  leave_type: leaveTypeMap[data.type] || 'annual',
  start_date: data.start,
  end_date: data.end,
  reason: data.reason,
  handover_notes: data.handover || '',
  approver: data.approver_id || null,
});

export const leaveService = {
  getAll: async () => {
    const response = await api.get('/leaves/');
    // /leaves/ is DRF-paginated ({count,results}); unwrap before mapping so the
    // list never silently becomes empty (regression from global pagination).
    // TODO(deferred): fetches only the first page (50 leaves). Add a page_size
    // param or pagination UI when a single user can exceed 50 applications.
    return { data: unwrapPaginated(response).map(mapLeave) };
  },

  // Actionable pending-approval queue for the current user — driven by the shared
  // backend resolver (leaves.approvals), the SAME source as the notifications, so
  // every "awaiting your review" item appears here.
  getPendingApprovals: async () => {
    const response = await api.get('/leaves/', { params: { queue: 'actionable' } });
    return { data: unwrapPaginated(response).map(mapLeave) };
  },

  getBalances: async () => {
    const response = await api.get('/leaves/balance');
    return { data: response.data };
  },

  // Category-aware entitlement view for the dashboard (cards + comp + category).
  getEntitlements: async () => (await api.get('/leaves/my-entitlements/')).data,
  // Official category-based leave policy (A–D), driven live from the entitlement
  // engine so it can never drift from the balance cards.
  getLeavePolicy: async () => (await api.get('/leaves/leave-policy/')).data,

  create: async (data, employeeName) => {
    const response = await api.post('/leaves/', toBackendPayload(data));
    const leave = mapLeave(response.data);
    leave.employee = employeeName;
    return { data: leave };
  },

  updateStatus: async (id, status, remarks = '') => {
    const response = await api.post(`/leaves/${encodeURIComponent(id)}/set_status/`, { status, remarks });
    return { data: mapLeave(response.data) };
  },

  // Leave review. The Department Head's approval is FINAL and grants the leave:
  //   pending    -> dept-head-review: approve => APPROVED (granted + balance), reject
  //   pending_hr -> hr-review:        legacy two-stage rows only (finalize/reject)
  // HR/Admin act via dept-head-review only as a fallback when a department has no
  // Department Head. `status` is the UI decision ('approved' | 'rejected').
  reviewLeave: async (id, currentStatus, status, remarks = '') => {
    const decision = status === 'approved' ? 'approve' : 'reject';
    const path = currentStatus === 'pending_hr' ? 'hr-review' : 'dept-head-review';
    const response = await api.post(`/leaves/${encodeURIComponent(id)}/${path}/`, { decision, remarks });
    return { data: mapLeave(response.data) };
  },

  // Full, un-mapped detail for the review panel (employee id, BS dates,
  // balance, timeline, etc.). Kept raw so the modal sees every enriched field.
  getById: async (id) => {
    const response = await api.get(`/leaves/${encodeURIComponent(id)}/`);
    return response.data;
  },
};
