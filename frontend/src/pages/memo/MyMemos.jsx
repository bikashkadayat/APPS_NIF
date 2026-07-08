import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { memoService } from '../../services/memoService';
import MemoTable from '../../components/memo/MemoTable';
import { Skeleton, EmptyState, ErrorState } from '../../components/leave-records/States';

const TABS = ['All', 'draft', 'submitted', 'approved', 'rejected'];

const MyMemos = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [tab, setTab] = useState('All');

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['memos', 'mine'],
    queryFn: () => memoService.listMemos({}, 1),
  });

  const mine = useMemo(() => {
    const rows = (data?.items ?? []).filter((m) => String(m.created_by?.id) === String(user?.id));
    return tab === 'All' ? rows : rows.filter((m) => m.status === tab);
  }, [data, user, tab]);

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <div className="lr-page-head">
        <div><h2>My Memos</h2><div className="lr-page-sub">Memos you created</div></div>
        <button type="button" className="lr-btn lr-btn-primary" onClick={() => navigate('/memos/create')}><Plus size={14} /> Create Memo</button>
      </div>

      <div className="lr-tabs" style={{ marginBottom: 16 }}>
        {TABS.map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t}
            className={`lr-tab ${tab === t ? 'on' : ''}`} onClick={() => setTab(t)} style={{ textTransform: 'capitalize' }}>{t}</button>
        ))}
      </div>

      {isLoading && <Skeleton rows={4} />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {!isLoading && !isError && mine.length === 0 && (
        <EmptyState message="You haven't created any memos yet." ctaLabel="Create Memo" ctaTo="/memos/create" />
      )}
      {!isLoading && !isError && mine.length > 0 && <MemoTable items={mine} />}
    </div>
  );
};

export default MyMemos;
