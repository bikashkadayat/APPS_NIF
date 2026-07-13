import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileDown, Loader } from 'lucide-react';
import { memoService } from '../../services/memoService';
import { documentService, saveBlob } from '../../services/documentService';
import { MemoStatusBadge, MemoPriorityBadge, MemoTypeBadge } from '../../components/memo/badges';
import RichTextEditor from '../../components/memo/RichTextEditor';
import UserSelector from '../../components/memo/UserSelector';
import ApprovalTimeline from '../../components/memo/ApprovalTimeline';
import Toast from '../../components/admin/Toast';
import { Skeleton, ErrorState } from '../../components/leave-records/States';

/** Modal that collects a comment (+ optional approver) for a workflow action. */
const ActionModal = ({ title, needsComment, minComment = 10, needsApprover, busy, onClose, onSubmit }) => {
  const [comment, setComment] = useState('');
  const [approver, setApprover] = useState('');
  const commentOk = !needsComment || comment.trim().length >= minComment;
  return (
    <div className="lr-modal-overlay" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="lr-modal" onClick={(e) => e.stopPropagation()}>
        <div className="lr-modal-head"><h3>{title}</h3><button type="button" className="lr-modal-close" aria-label="Close" onClick={onClose}>×</button></div>
        {needsApprover && (
          <label className="lr-field"><span>Assign Approver</span>
            <UserSelector role="approver" value={approver} onChange={setApprover} allowAuto />
          </label>
        )}
        <label className="lr-field"><span>Comment {needsComment && <span aria-hidden>* (min {minComment} chars)</span>}</span>
          <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} aria-label="Comment" />
        </label>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
          <button type="button" className="lr-btn lr-btn-ghost" onClick={onClose}>Cancel</button>
          <button type="button" className="lr-btn lr-btn-primary" disabled={!commentOk || busy}
            onClick={() => onSubmit({ comment, override_approver_id: approver || undefined })}>
            {busy ? 'Working…' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
};

const MemoDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [modal, setModal] = useState(null); // {type}
  const [toast, setToast] = useState(null);
  const [pdfBusy, setPdfBusy] = useState(false);

  const { data: memo, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['memo', id], queryFn: () => memoService.getMemo(id),
  });

  const done = (msg) => { setToast({ message: msg, tone: 'success' }); setModal(null); qc.invalidateQueries({ queryKey: ['memo', id] }); qc.invalidateQueries({ queryKey: ['memos'] }); };
  const fail = (e) => setToast({ message: e?.response?.data?.detail || e?.response?.data?.comment || 'Action failed.', tone: 'error' });

  const act = useMutation({
    mutationFn: async ({ type, comment, override_approver_id }) => {
      if (type === 'submit') return memoService.submitMemo(id);
      if (type === 'cancel') return memoService.cancelMemo(id);
      if (type === 'review') return memoService.reviewMemo(id, { comment, override_approver_id });
      if (type === 'approve') return memoService.approveMemo(id, { comment });
      if (type === 'reject') return memoService.rejectMemo(id, { comment });
      if (type === 'return') return memoService.returnMemo(id, { comment });
      return null;
    },
    onSuccess: (_r, v) => done(`Memo ${v.type}${v.type.endsWith('e') ? 'd' : 'ed'}.`),
    onError: fail,
  });

  const duplicate = useMutation({
    mutationFn: () => memoService.createMemo({ title: memo.title, subject: memo.subject, body: memo.body, memo_type: memo.memo_type, priority: memo.priority }),
    onSuccess: (m) => navigate(`/memos/${m.id}`),
    onError: fail,
  });

  const downloadPdf = async () => {
    setPdfBusy(true);
    try { saveBlob(await documentService.memoPdf(id), `${memo.memo_number}.pdf`); }
    catch { setToast({ message: 'PDF download failed.', tone: 'error' }); }
    finally { setPdfBusy(false); }
  };

  if (isLoading) return <div className="page"><Skeleton rows={4} /></div>;
  if (isError) return <div className="page"><ErrorState error={error} onRetry={refetch} /></div>;

  const name = (u) => u?.full_name || '—';

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <button type="button" className="lr-btn lr-btn-ghost" onClick={() => navigate(-1)} style={{ marginBottom: 16 }}><ArrowLeft size={14} /> Back</button>

      <div className="lr-page-head">
        <div className="memo-head">
          <div className="memo-head-number">{memo.memo_number}</div>
          <h1 className="memo-head-title">{memo.title}</h1>
          <div className="memo-head-badges">
            <MemoStatusBadge status={memo.status} />
            <MemoPriorityBadge priority={memo.priority} />
            <MemoTypeBadge memo_type={memo.memo_type} />
          </div>
        </div>
        {memo.status === 'approved' && (
          <button type="button" className="lr-btn" onClick={downloadPdf} disabled={pdfBusy}>
            {pdfBusy ? <Loader size={14} className="lr-spin" /> : <FileDown size={14} />} Download PDF
          </button>
        )}
      </div>

      <div className="lr-memo-detail">
        <div>
          <div className="lr-chart-card">
            <div style={{ fontWeight: 700, marginBottom: 8 }}>{memo.subject}</div>
            <RichTextEditor value={memo.body} readOnly />
            {memo.attachment_url && (
              <p style={{ marginTop: 12 }}><a href={memo.attachment_url} target="_blank" rel="noreferrer" className="lr-btn lr-btn-ghost"><FileDown size={13} /> Attachment</a></p>
            )}
          </div>
          <h3 className="lr-chart-title" style={{ marginTop: 20 }}>Approval trail</h3>
          <ApprovalTimeline steps={memo.approval_steps} />
        </div>

        <aside>
          <div className="side-card" style={{ padding: 18, marginBottom: 16 }}>
            <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)', marginBottom: 12 }}>Details</h3>
            <dl className="lr-modal-grid" style={{ gridTemplateColumns: '1fr' }}>
              <div><dt>Created by</dt><dd>{name(memo.created_by)}</dd></div>
              <div><dt>Checker</dt><dd>{name(memo.current_reviewer)}</dd></div>
              <div><dt>Approver</dt><dd>{name(memo.current_approver)}</dd></div>
              <div><dt>Created</dt><dd>{new Date(memo.created_at).toLocaleString()}</dd></div>
              {memo.submitted_at && <div><dt>Submitted</dt><dd>{new Date(memo.submitted_at).toLocaleString()}</dd></div>}
              {memo.finalized_at && <div><dt>Finalized</dt><dd>{new Date(memo.finalized_at).toLocaleString()}</dd></div>}
            </dl>
          </div>

          <div className="side-card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)' }}>Actions</h3>
            {memo.can_submit && <button type="button" className="lr-btn lr-btn-primary" onClick={() => act.mutate({ type: 'submit' })}>Submit for review</button>}
            {memo.can_edit && <button type="button" className="lr-btn lr-btn-ghost" onClick={() => setModal({ type: 'cancel' })}>Cancel memo</button>}
            {memo.can_review && <>
              <button type="button" className="lr-btn lr-btn-primary" onClick={() => setModal({ type: 'review' })}>Review → approver</button>
              <button type="button" className="lr-btn lr-btn-ghost" onClick={() => setModal({ type: 'return' })}>Return to author</button>
            </>}
            {memo.can_approve && <button type="button" className="lr-btn lr-btn-primary" onClick={() => setModal({ type: 'approve' })}>Approve</button>}
            {memo.can_reject && <button type="button" className="lr-btn lr-btn-danger" onClick={() => setModal({ type: 'reject' })}>Reject</button>}
            {memo.status === 'rejected' && memo.can_edit === false && (
              <button type="button" className="lr-btn lr-btn-ghost" onClick={() => duplicate.mutate()} disabled={duplicate.isPending}>Duplicate as new draft</button>
            )}
          </div>
        </aside>
      </div>

      {modal?.type === 'cancel' && (
        <div className="lr-modal-overlay" role="dialog" aria-modal="true" aria-label="Cancel memo" onClick={() => setModal(null)}>
          <div className="lr-modal" onClick={(e) => e.stopPropagation()}>
            <div className="lr-modal-head"><h3>Cancel this memo?</h3></div>
            <p style={{ fontSize: 14 }}>This moves the memo to Cancelled.</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12 }}>
              <button type="button" className="lr-btn lr-btn-ghost" onClick={() => setModal(null)}>Keep</button>
              <button type="button" className="lr-btn lr-btn-danger" disabled={act.isPending} onClick={() => act.mutate({ type: 'cancel' })}>Cancel memo</button>
            </div>
          </div>
        </div>
      )}
      {modal?.type === 'review' && <ActionModal title="Review & forward to approver" needsApprover busy={act.isPending} onClose={() => setModal(null)} onSubmit={(v) => act.mutate({ type: 'review', ...v })} />}
      {modal?.type === 'approve' && <ActionModal title="Approve memo" busy={act.isPending} onClose={() => setModal(null)} onSubmit={(v) => act.mutate({ type: 'approve', ...v })} />}
      {modal?.type === 'reject' && <ActionModal title="Reject memo" needsComment busy={act.isPending} onClose={() => setModal(null)} onSubmit={(v) => act.mutate({ type: 'reject', ...v })} />}
      {modal?.type === 'return' && <ActionModal title="Return to author" needsComment busy={act.isPending} onClose={() => setModal(null)} onSubmit={(v) => act.mutate({ type: 'return', ...v })} />}
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
};

export default MemoDetail;
