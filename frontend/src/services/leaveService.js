import api from './api';

const leaveTypeMap = {
  'Annual Leave': 'annual',
  'Sick Leave': 'sick',
  'Casual Leave': 'casual',
};

const apiToUiType = {
  annual: 'Annual Leave',
  sick: 'Sick Leave',
  casual: 'Casual Leave',
};

const calculateDays = (start, end) => {
  const d1 = new Date(start);
  const d2 = new Date(end);
  const diff = Math.abs(d2 - d1);
  return Math.ceil(diff / (1000 * 60 * 60 * 24)) + 1;
};

const mapLeave = (leave) => ({
  id: leave.id,
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
    return { data: response.data.map(mapLeave) };
  },

  getBalances: async () => {
    const response = await api.get('/leaves/balance');
    return { data: response.data };
  },

  create: async (data, employeeName) => {
    const response = await api.post('/leaves/', toBackendPayload(data));
    const leave = mapLeave(response.data);
    leave.employee = employeeName;
    return { data: leave };
  },

  updateStatus: async (id, status) => {
    const response = await api.post(`/leaves/${encodeURIComponent(id)}/set_status/`, { status });
    return { data: mapLeave(response.data) };
  }
};
