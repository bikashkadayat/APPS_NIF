import api from './api';

// DRF list endpoints are paginated ({count, results}); unwrap to the array.
const list = (res) => (Array.isArray(res.data) ? res.data : res.data?.results || []);

export const inventoryService = {
  // Categories
  categories: async () => list(await api.get('/inventory/categories/')),

  // Items
  items: async (params = {}) => list(await api.get('/inventory/items/', { params })),
  item: async (id) => (await api.get(`/inventory/items/${id}/`)).data,
  createItem: async (payload) => (await api.post('/inventory/items/', payload)).data,
  updateItem: async (id, payload) => (await api.patch(`/inventory/items/${id}/`, payload)).data,
  deleteItem: async (id) => { await api.delete(`/inventory/items/${id}/`); },
  assignItem: async (id, payload) => (await api.post(`/inventory/items/${id}/assign/`, payload)).data,
  handoverItem: async (id, payload) => (await api.post(`/inventory/items/${id}/handover/`, payload)).data,
  returnItem: async (id, payload = {}) => (await api.post(`/inventory/items/${id}/return/`, payload)).data,
  assignments: async (id) => list(await api.get(`/inventory/items/${id}/assignments/`)),
  // Cross-item "who has what" board (managers) + employee "My Assigned Assets".
  board: async (params = {}) => list(await api.get('/inventory/assignments/', { params })),
  myAssets: async () => list(await api.get('/inventory/assignments/mine/')),
  assignmentReceipt: async (id) => {
    const res = await api.get(`/inventory/items/${id}/assignment-receipt/`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
    window.open(url, '_blank', 'noopener');
    setTimeout(() => window.URL.revokeObjectURL(url), 60000);
  },

  // Take-out requests
  takeouts: async (params = {}) => list(await api.get('/inventory/takeouts/', { params })),
  createTakeout: async (payload) => (await api.post('/inventory/takeouts/', payload)).data,
  approveTakeout: async (id, remarks = '') =>
    (await api.post(`/inventory/takeouts/${id}/approve/`, { remarks })).data,
  rejectTakeout: async (id, remarks) =>
    (await api.post(`/inventory/takeouts/${id}/reject/`, { remarks })).data,
  markReturned: async (id) => (await api.post(`/inventory/takeouts/${id}/mark_returned/`, {})).data,

  // Gate pass PDF (blob) — open in a new tab.
  gatePass: async (id) => {
    const res = await api.get(`/inventory/takeouts/${id}/gate-pass/`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
    window.open(url, '_blank', 'noopener');
    setTimeout(() => window.URL.revokeObjectURL(url), 60000);
  },

  // Active employees (managers only) with name + department for the assign UI.
  employees: async () => list(await api.get('/inventory/employees/')),
};
