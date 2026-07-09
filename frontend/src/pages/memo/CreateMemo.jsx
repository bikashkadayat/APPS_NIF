import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Paperclip } from 'lucide-react';
import { memoService } from '../../services/memoService';
import RichTextEditor from '../../components/memo/RichTextEditor';
import UserSelector from '../../components/memo/UserSelector';
import { MemoTypeBadge, MemoPriorityBadge } from '../../components/memo/badges';
import ConfirmModal from '../../components/admin/ConfirmModal';

const TYPES = ['general', 'hr', 'financial', 'internal', 'external'];
const PRIORITIES = ['low', 'normal', 'high', 'urgent'];

const CreateMemo = () => {
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const [form, setForm] = useState({ title: '', subject: '', memo_type: 'general', priority: 'normal', body: '' });
  const [checker, setChecker] = useState('');
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [created, setCreated] = useState(null); // {id, memo_number}
  const [cancelling, setCancelling] = useState(false);

  const { data: templates = [] } = useQuery({ queryKey: ['memo-templates'], queryFn: memoService.listTemplates });

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const dirty = form.title || form.subject || form.body || file;
  const valid = form.title.trim() && form.subject.trim();

  const loadTemplate = (id) => {
    const t = templates.find((x) => String(x.id) === String(id));
    if (!t) return;
    setForm((f) => ({ ...f, memo_type: t.memo_type || f.memo_type, subject: t.subject_template || '', body: t.body_template || '' }));
  };

  // Build a JSON object, or FormData when an attachment is present; the service
  // handles both (M5). `extra` carries submit-only fields (override_reviewer_id).
  const buildBody = (extra = {}) => {
    const fields = { ...form, ...extra };
    if (!file) return fields;
    const fd = new FormData();
    Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
    fd.append('attachment', file);
    return fd;
  };

  const saveDraft = useMutation({
    mutationFn: () => memoService.createMemo(buildBody()),
    onSuccess: (memo) => setCreated({ id: memo.id, memo_number: memo.memo_number }),
    onError: (e) => setError(e?.response?.data?.detail || 'Could not save memo.'),
  });

  const submitForReview = useMutation({
    // Atomic create+submit (M2): a failed submit leaves no orphaned draft.
    mutationFn: () => memoService.createAndSubmit(buildBody(checker ? { override_reviewer_id: checker } : {})),
    onSuccess: (memo) => setCreated({ id: memo.id, memo_number: memo.memo_number, submitted: true }),
    onError: (e) => setError(e?.response?.data?.detail || e?.response?.data?.override_reviewer_id?.[0] || 'Could not submit memo.'),
  });

  const busy = saveDraft.isPending || submitForReview.isPending;

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <div className="lr-page-head">
        <div><h2>Create Memo</h2><div className="lr-page-sub">Available to all roles · draft or submit for review</div></div>
      </div>

      <div className="lr-memo-create">
        {/* form */}
        <div>
          <label className="lr-field"><span>Load from template (optional)</span>
            <select defaultValue="" onChange={(e) => loadTemplate(e.target.value)} aria-label="Load template">
              <option value="">— none —</option>
              {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
          <label className="lr-field"><span>Title <span aria-hidden>*</span></span><input value={form.title} onChange={set('title')} aria-label="Title" /></label>
          <label className="lr-field"><span>Subject <span aria-hidden>*</span></span><input value={form.subject} onChange={set('subject')} aria-label="Subject" /></label>
          <div style={{ display: 'flex', gap: 12 }}>
            <label className="lr-field" style={{ flex: 1 }}><span>Type</span>
              <select value={form.memo_type} onChange={set('memo_type')} aria-label="Type">{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select>
            </label>
            <label className="lr-field" style={{ flex: 1 }}><span>Priority</span>
              <select value={form.priority} onChange={set('priority')} aria-label="Priority">{PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}</select>
            </label>
          </div>
          <div className="lr-field"><span>Body</span>
            <RichTextEditor value={form.body} onChange={(html) => setForm((f) => ({ ...f, body: html }))} />
          </div>
          <div className="lr-field"><span>Attachment (optional, ≤ 10MB)</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <button type="button" className="lr-btn lr-btn-ghost" onClick={() => fileRef.current?.click()}><Paperclip size={14} /> Choose file</button>
              <span className="lr-page-sub">{file ? file.name : 'No file chosen'}</span>
              <input ref={fileRef} type="file" hidden onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </div>
          </div>
          <label className="lr-field"><span>Assign Checker</span>
            <UserSelector role="checker" value={checker} onChange={setChecker} allowAuto />
          </label>
          <p className="lr-page-sub">The approver is assigned by the checker during review.</p>
          {error && <p role="alert" style={{ color: 'var(--danger)', fontSize: 13 }}>{error}</p>}
        </div>

        {/* live preview */}
        <aside className="lr-memo-preview">
          <div className="lr-chart-card">
            <div className="lr-chart-title">Preview</div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
              <MemoTypeBadge memo_type={form.memo_type} /><MemoPriorityBadge priority={form.priority} />
            </div>
            <h3 style={{ margin: '4px 0' }}>{form.title || 'Untitled memo'}</h3>
            <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>{form.subject || 'Subject'}</div>
            <RichTextEditor value={form.body} readOnly />
          </div>
        </aside>
      </div>

      <div className="lr-memo-actionbar">
        <button type="button" className="lr-btn lr-btn-ghost" onClick={() => (dirty ? setCancelling(true) : navigate('/memos/my'))}>Cancel</button>
        <button type="button" className="lr-btn" disabled={!valid || busy} onClick={() => { setError(null); saveDraft.mutate(); }}>Save as Draft</button>
        <button type="button" className="lr-btn lr-btn-primary" disabled={!valid || busy} onClick={() => { setError(null); submitForReview.mutate(); }}>
          {busy ? 'Working…' : 'Submit for Review'}
        </button>
      </div>

      {cancelling && (
        <ConfirmModal title="Discard this memo?" message="Your unsaved changes will be lost." danger confirmLabel="Discard"
          onClose={() => setCancelling(false)} onConfirm={() => navigate('/memos/my')} />
      )}

      {created && (
        <div className="lr-modal-overlay" role="dialog" aria-modal="true" aria-label="Memo created">
          <div className="lr-modal" onClick={(e) => e.stopPropagation()}>
            <div className="lr-modal-head"><h3>Memo {created.submitted ? 'submitted' : 'saved'}!</h3></div>
            <p style={{ fontSize: 14 }}>Number: <b>{created.memo_number}</b>{created.submitted ? ' — sent for review.' : ' — saved as draft.'}</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 14 }}>
              <button type="button" className="lr-btn lr-btn-ghost" onClick={() => { setCreated(null); setForm({ title: '', subject: '', memo_type: 'general', priority: 'normal', body: '' }); setChecker(''); setFile(null); }}>Create Another</button>
              <button type="button" className="lr-btn lr-btn-primary" onClick={() => navigate(`/memos/${created.id}`)}>View Memo</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CreateMemo;
