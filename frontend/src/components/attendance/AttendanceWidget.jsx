import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { LogIn, LogOut, Clock, CheckCircle } from 'lucide-react';
import { attendanceService } from '../../services/attendanceService';

const STATUS_META = {
  present: { label: 'Present', color: 'var(--success)' },
  late: { label: 'Late', color: 'var(--warning)' },
  half_day: { label: 'Half Day', color: '#eab308' },
  absent: { label: 'Absent', color: 'var(--danger)' },
  on_leave: { label: 'On Leave', color: 'var(--brand-blue)' },
  holiday: { label: 'Holiday', color: 'var(--text-muted)' },
};

const Stat = ({ label, value, color }) => (
  <div className="att-stat">
    <div className="att-stat-val" style={{ color }}>{value}</div>
    <div className="att-stat-lbl">{label}</div>
  </div>
);

const AttendanceWidget = () => {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['attendance', 'today'], queryFn: attendanceService.today });
  const [err, setErr] = React.useState('');

  const act = useMutation({
    mutationFn: (kind) => (kind === 'in' ? attendanceService.checkIn() : attendanceService.checkOut()),
    onSuccess: () => { setErr(''); qc.invalidateQueries({ queryKey: ['attendance', 'today'] }); },
    onError: (e) => setErr(e?.response?.data?.detail || 'Action failed.'),
  });

  if (isLoading) return <div className="table-card att-card">Loading attendance…</div>;
  const t = data || {};
  const m = t.month_summary || {};
  const meta = STATUS_META[t.status] || { label: t.status || '—', color: 'var(--text-secondary)' };

  return (
    <div className="table-card att-card">
      <div className="att-head">
        <h3><Clock size={18} /> My Attendance</h3>
        <div className="att-date">B.S. {t.date_bs} · {t.date}</div>
      </div>

      <div className="att-today">
        <div>
          <div className="att-today-lbl">Today's status</div>
          <div className="att-today-status" style={{ color: meta.color }}>
            <CheckCircle size={16} /> {meta.label}
          </div>
          <div className="att-today-times">
            In: <strong>{t.check_in_local || '—'}</strong> · Out: <strong>{t.check_out_local || '—'}</strong> · Hours: <strong>{t.working_hours}</strong>
            <span className="att-office"> (office starts {t.office_start})</span>
          </div>
        </div>
        <div className="att-actions">
          <button type="button" className="btn btn-success" disabled={!t.can_check_in || act.isPending} onClick={() => act.mutate('in')}>
            <LogIn size={16} /> Check In
          </button>
          <button type="button" className="btn btn-primary" disabled={!t.can_check_out || act.isPending} onClick={() => act.mutate('out')}>
            <LogOut size={16} /> Check Out
          </button>
        </div>
      </div>
      {err && <div className="att-err">{err}</div>}

      <div className="att-stats">
        <Stat label="Present" value={(m.present || 0) + (m.late || 0)} color="var(--success)" />
        <Stat label="On Leave" value={m.on_leave || 0} color="var(--brand-blue)" />
        <Stat label="Absent" value={m.absent || 0} color="var(--danger)" />
        <Stat label="Holidays" value={m.holiday || 0} color="var(--text-muted)" />
      </div>
      <div className="att-foot">This month · present includes late days</div>
    </div>
  );
};

export default AttendanceWidget;
