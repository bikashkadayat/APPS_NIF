import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { memoService } from '../../services/memoService';
import MemoTable from '../../components/memo/MemoTable';
import { Skeleton, EmptyState, ErrorState } from '../../components/leave-records/States';

const MemoList = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [type, setType] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['memos', 'all', page],
    queryFn: () => memoService.listMemos({}, page),
  });

  // Filters applied client-side over the current page (backend list is unfiltered).
  const items = useMemo(() => {
    let rows = data?.items ?? [];
    if (status) rows = rows.filter((m) => m.status === status);
    if (type) rows = rows.filter((m) => m.memo_type === type);
    if (search) {
      const q = search.toLowerCase();
      rows = rows.filter((m) => m.title?.toLowerCase().includes(q) || m.memo_number?.toLowerCase().includes(q));
    }
    return rows;
  }, [data, status, type, search]);

  const count = data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(count / 50));

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <div className="lr-page-head">
        <div><h2>All Memos</h2><div className="lr-page-sub">Memos visible to you ({count})</div></div>
        <button type="button" className="lr-btn lr-btn-primary" onClick={() => navigate('/memos/create')}><Plus size={14} /> Create Memo</button>
      </div>

      <div className="lr-filter-bar">
        <input type="search" placeholder="Search title / number" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search memos" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {['draft', 'submitted', 'under_review', 'approved', 'rejected', 'cancelled'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={type} onChange={(e) => setType(e.target.value)} aria-label="Filter by type">
          <option value="">All types</option>
          {['general', 'hr', 'financial', 'internal', 'external'].map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {isLoading && <Skeleton rows={4} />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {!isLoading && !isError && items.length === 0 && (
        <EmptyState message="No memos yet." ctaLabel="Create Memo" ctaTo="/memos/create" />
      )}
      {!isLoading && !isError && items.length > 0 && (
        <>
          <MemoTable items={items} />
          {totalPages > 1 && (
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16, alignItems: 'center' }}>
              <button type="button" className="lr-btn lr-btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <span className="lr-page-sub">Page {page} of {totalPages}</span>
              <button type="button" className="lr-btn lr-btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default MemoList;
