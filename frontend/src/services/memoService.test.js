import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./api', () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
import api from './api';
import { memoService } from './memoService';

describe('memoService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('listMemos unwraps a paginated response', async () => {
    api.get.mockResolvedValue({ data: { count: 2, next: null, previous: null, results: [{ id: '1' }, { id: '2' }] } });
    const res = await memoService.listMemos({ status: 'draft' }, 2);
    expect(api.get).toHaveBeenCalledWith('/memos/', { params: { status: 'draft', page: 2 } });
    expect(res.items).toHaveLength(2);
    expect(res.count).toBe(2);
  });

  it('createMemo returns id + memo_number', async () => {
    api.post.mockResolvedValue({ data: { id: 'm1', memo_number: 'NIFN-GEN-2026-0001', status: 'draft' } });
    const memo = await memoService.createMemo({ title: 'T' });
    expect(api.post).toHaveBeenCalledWith('/memos/', { title: 'T' });
    expect(memo).toMatchObject({ id: 'm1', memo_number: 'NIFN-GEN-2026-0001' });
  });

  it('createMemo with an attachment uses the service multipart path (M5)', async () => {
    api.post.mockResolvedValue({ data: { id: 'm1' } });
    const fd = new FormData();
    fd.append('title', 'T');
    fd.append('attachment', new Blob(['x']), 'f.pdf');
    await memoService.createMemo(fd);
    expect(api.post).toHaveBeenCalledWith('/memos/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  });

  it('createAndSubmit posts to the atomic endpoint (M2)', async () => {
    api.post.mockResolvedValue({ data: { id: 'm1', status: 'submitted' } });
    await memoService.createAndSubmit({ title: 'T', override_reviewer_id: 'c1' });
    expect(api.post).toHaveBeenCalledWith('/memos/create-and-submit/', { title: 'T', override_reviewer_id: 'c1' });
  });

  it('submitMemo posts to the submit action with override', async () => {
    api.post.mockResolvedValue({ data: {} });
    await memoService.submitMemo('m1', { override_reviewer_id: 'c1' });
    expect(api.post).toHaveBeenCalledWith('/memos/m1/submit/', { override_reviewer_id: 'c1' });
  });

  it('reviewMemo/approveMemo/rejectMemo/returnMemo/cancelMemo hit the right paths', async () => {
    api.post.mockResolvedValue({ data: {} });
    await memoService.reviewMemo('m1', { comment: 'ok', override_approver_id: 'a1' });
    expect(api.post).toHaveBeenCalledWith('/memos/m1/review/', { action: 'reviewed', comment: 'ok', override_approver_id: 'a1' });
    await memoService.approveMemo('m1', { comment: 'go' });
    expect(api.post).toHaveBeenCalledWith('/memos/m1/approve/', { action: 'approved', comment: 'go' });
    await memoService.rejectMemo('m1', { comment: 'no good enough' });
    expect(api.post).toHaveBeenCalledWith('/memos/m1/reject/', { action: 'rejected', comment: 'no good enough' });
    await memoService.returnMemo('m1', { comment: 'revise please' });
    expect(api.post).toHaveBeenCalledWith('/memos/m1/return/', { action: 'returned', comment: 'revise please' });
    await memoService.cancelMemo('m1');
    expect(api.post).toHaveBeenCalledWith('/memos/m1/cancel/', {});
  });

  it('listTemplates unwraps paginated templates', async () => {
    api.get.mockResolvedValue({ data: { count: 1, results: [{ id: 't1', name: 'HR Notice' }] } });
    const t = await memoService.listTemplates();
    expect(api.get).toHaveBeenCalledWith('/memo-templates/');
    expect(t).toHaveLength(1);
  });
});
