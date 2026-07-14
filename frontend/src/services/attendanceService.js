import api from './api';

/** Attendance: check-in/out, today's status, and monthly calendar. */
export const attendanceService = {
  today: async () => (await api.get('/attendance/today/')).data,
  checkIn: async () => (await api.post('/attendance/check-in/', {})).data,
  checkOut: async () => (await api.post('/attendance/check-out/', {})).data,
  myCalendar: async (year, month) =>
    (await api.get('/attendance/me/', { params: { year, month } })).data,
  list: async (params = {}) => (await api.get('/attendance/', { params })).data,
  manual: async (payload) => (await api.post('/attendance/manual/', payload)).data,

  // HR/Admin-safe options (employees + departments) for the reports dropdowns.
  reportOptions: async () => (await api.get('/attendance/report/options/')).data,

  // Report exports (Admin/HR). Return the full axios response (blob) for saveBlob.
  reportWeekly: (id, week) => api.get(`/attendance/report/employee/${id}/weekly`, { params: { week }, responseType: 'blob' }),
  reportMonthly: (id, year, month) => api.get(`/attendance/report/employee/${id}/monthly`, { params: { year, month }, responseType: 'blob' }),
  reportAll: (params) => api.get('/attendance/report/all', { params, responseType: 'blob' }),
};

export default attendanceService;
