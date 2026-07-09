import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { memoService } from '../../services/memoService';

const MIN_QUERY = 2; // server rejects shorter queries (H5)

/**
 * Dropdown to pick a checker/approver, with an optional "Auto-assign" choice.
 * Results are fetched from the server per search term (min 2 chars) rather than
 * loading the whole roster, so the directory cannot be enumerated (H5).
 *
 * @param {{ role:'checker'|'approver', value:string, onChange:(id:string)=>void,
 *           allowAuto?:boolean }} props  value '' means auto-assign.
 */
const UserSelector = ({ role, value, onChange, allowAuto = true }) => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const query = search.trim();
  const enabled = query.length >= MIN_QUERY;

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['memo-assignees', role, query],
    queryFn: () => (role === 'approver'
      ? memoService.getAvailableApprovers(query)
      : memoService.getAvailableCheckers(query)),
    enabled,
    staleTime: 30_000,
  });

  const filtered = users;

  const selected = users.find((u) => String(u.id) === String(value));
  const label = value ? (selected ? selected.full_name : 'Selected user')
    : (allowAuto ? 'Auto-assign by department' : 'Select…');

  const pick = (id) => { onChange(id); setOpen(false); setSearch(''); };

  return (
    <div className="lr-userselect">
      <button type="button" className="lr-userselect-trigger" aria-haspopup="listbox" aria-expanded={open}
        onClick={() => setOpen((o) => !o)}>
        <span>{label}</span>
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="lr-userselect-menu" role="listbox">
          <input autoFocus type="search" placeholder={`Search ${role}s…`} value={search}
            onChange={(e) => setSearch(e.target.value)} aria-label={`Search ${role}s`} className="lr-userselect-search" />
          {allowAuto && (
            <button type="button" role="option" aria-selected={!value} className={`lr-userselect-opt ${!value ? 'on' : ''}`} onClick={() => pick('')}>
              <b>Auto-assign by department</b>
            </button>
          )}
          {!enabled && <div className="lr-userselect-empty">Type at least {MIN_QUERY} characters to search {role}s.</div>}
          {enabled && isLoading && <div className="lr-userselect-empty">Loading…</div>}
          {enabled && !isLoading && filtered.length === 0 && <div className="lr-userselect-empty">No matching {role}s.</div>}
          {filtered.map((u) => (
            <button key={u.id} type="button" role="option" aria-selected={String(u.id) === String(value)}
              className={`lr-userselect-opt ${String(u.id) === String(value) ? 'on' : ''}`} onClick={() => pick(String(u.id))}>
              <div>{u.full_name}</div>
              {u.department && <div className="lr-userselect-sub">{u.department}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default UserSelector;
