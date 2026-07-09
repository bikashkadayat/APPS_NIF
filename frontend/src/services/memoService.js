import api from './api';
import { unwrapPaginated } from './utils';

/** POST a memo payload, letting the browser set the multipart boundary for FormData. */
const postMemo = (url, data) => {
  const isForm = typeof FormData !== 'undefined' && data instanceof FormData;
  return isForm
    ? api.post(url, data, { headers: { 'Content-Type': 'multipart/form-data' } })
    : api.post(url, data);
};

/**
 * Memo module service (Phase 3). Talks to /api/v1/memos/* which implements the
 * 3-level workflow (maker/any -> checker -> approver). Uses the shared axios
 * instance (auto token refresh).
 */
export const memoService = {
  /**
   * @param {Object} filters query params (status, memo_type, priority, search…)
   * @param {number} page
   * @returns {Promise<{items:Object[], count:number, next:?string, previous:?string}>}
   */
  listMemos: async (filters = {}, page = 1) => {
    const res = await api.get('/memos/', { params: { ...filters, page } });
    return {
      items: unwrapPaginated(res),
      count: res.data?.count ?? (Array.isArray(res.data) ? res.data.length : 0),
      next: res.data?.next ?? null,
      previous: res.data?.previous ?? null,
    };
  },

  /** @returns {Promise<Object>} full memo detail incl. approval_steps + can_* flags */
  getMemo: async (id) => (await api.get(`/memos/${id}/`)).data,

  /**
   * Create a draft memo. Accepts either a plain object (JSON) or a FormData
   * (when an attachment is included) - the single code path picks the right
   * content type (M5). @returns {Promise<Object>} created memo (id + memo_number)
   */
  createMemo: async (data) => (await postMemo('/memos/', data)).data,

  /**
   * Atomically create + submit a memo (M2). Same JSON/FormData handling as
   * createMemo. If the submit fails server-side the draft is rolled back.
   */
  createAndSubmit: async (data) => (await postMemo('/memos/create-and-submit/', data)).data,

  updateMemo: async (id, data) => (await api.patch(`/memos/${id}/`, data)).data,

  submitMemo: async (id, { override_reviewer_id } = {}) =>
    (await api.post(`/memos/${id}/submit/`, override_reviewer_id ? { override_reviewer_id } : {})).data,

  reviewMemo: async (id, { comment = '', override_approver_id } = {}) =>
    (await api.post(`/memos/${id}/review/`, { action: 'reviewed', comment, ...(override_approver_id ? { override_approver_id } : {}) })).data,

  approveMemo: async (id, { comment = '' } = {}) =>
    (await api.post(`/memos/${id}/approve/`, { action: 'approved', comment })).data,

  rejectMemo: async (id, { comment }) =>
    (await api.post(`/memos/${id}/reject/`, { action: 'rejected', comment })).data,

  returnMemo: async (id, { comment }) =>
    (await api.post(`/memos/${id}/return/`, { action: 'returned', comment })).data,

  cancelMemo: async (id) => (await api.post(`/memos/${id}/cancel/`, {})).data,

  /** @returns {Promise<Object[]>} active checkers (id, full_name, email, role, department) */
  getAvailableCheckers: async (search) =>
    (await api.get('/memos/available-checkers/', { params: search ? { search } : {} })).data,

  /** @returns {Promise<Object[]>} active approvers */
  getAvailableApprovers: async (search) =>
    (await api.get('/memos/available-approvers/', { params: search ? { search } : {} })).data,

  /** @returns {Promise<Object[]>} active memo templates */
  listTemplates: async () => unwrapPaginated(await api.get('/memo-templates/')),
};

export default memoService;
