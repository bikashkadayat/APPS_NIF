import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, ArrowRight, FileText } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { memoService } from '../../services/memoService';
import { can } from '../../services/roles';

const Tile = ({ label, value }) => (
  <div style={{ flex: 1, background: 'var(--bg-main)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
    <div style={{ fontFamily: '"Playfair Display", serif', fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{label}</div>
  </div>
);

/** Compact memo summary for the dashboard (all roles). */
const DashboardMemoCard = () => {
  const navigate = useNavigate();
  const { user, role } = useAuth();
  const { data } = useQuery({ queryKey: ['memos', 'dashboard'], queryFn: () => memoService.listMemos({}, 1) });
  const items = data?.items ?? [];
  const uid = String(user?.id);

  const mine = items.filter((m) => String(m.created_by?.id) === uid).length;
  const pending = items.filter((m) =>
    (String(m.current_reviewer?.id) === uid && m.status === 'submitted') ||
    (String(m.current_approver?.id) === uid && m.status === 'under_review')).length;

  return (
    <div className="table-card" style={{ padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: '"Playfair Display", serif', display: 'flex', alignItems: 'center', gap: 8 }}>
          <FileText size={18} /> Memos
        </h3>
        <button type="button" onClick={() => navigate('/memos')} style={{ background: 'none', border: 'none', color: 'var(--brand-blue)', fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          View all memos <ArrowRight size={14} />
        </button>
      </div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
        {/* "Created by me" is a personal widget — hidden for Admin (oversight only). */}
        {can(role, 'myMemos') && <Tile label="Created by me" value={mine} />}
        {(role === 'checker' || role === 'approver' || role === 'admin') && <Tile label="Pending my action" value={pending} />}
      </div>
      {can(role, 'createMemo') && (
        <button type="button" className="lr-btn lr-btn-primary" onClick={() => navigate('/memos/create')}><Plus size={14} /> Create Memo</button>
      )}
    </div>
  );
};

export default DashboardMemoCard;
