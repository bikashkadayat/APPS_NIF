import React, { useState } from 'react';
import { useTeamAttendance } from '../../../hooks/useLeaveRecords';
import { days } from '../../../utils/leaveFormat';
import AttendanceIndicator from '../../../components/leave-records/AttendanceIndicator';
import LeaveTypeChip from '../../../components/leave-records/LeaveTypeChip';
import { Skeleton, EmptyState, ErrorState } from '../../../components/leave-records/States';

const currentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

const TeamAttendance = () => {
  const [month, setMonth] = useState(currentMonth());
  const [dept, setDept] = useState('');
  const { data, isLoading, isError, error, refetch } = useTeamAttendance(dept || undefined, month);

  const team = data?.team ?? [];

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <div className="lr-page-head">
        <div>
          <h2>Team Attendance</h2>
          <div className="lr-page-sub">Monthly attendance heatmap for your team</div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <label className="lr-year-select">
            <span className="sr-only">Department code</span>
            <input
              type="text" placeholder="Dept code (optional)" value={dept}
              onChange={(e) => setDept(e.target.value.toUpperCase())}
              aria-label="Department code"
              style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', fontSize: 14 }}
            />
          </label>
          <label className="lr-year-select">
            <span className="sr-only">Month</span>
            <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} aria-label="Month"
              style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', fontSize: 14 }} />
          </label>
        </div>
      </div>

      {isLoading && <Skeleton rows={3} />}
      {isError && <ErrorState error={error} onRetry={refetch} />}
      {!isLoading && !isError && team.length === 0 && (
        <EmptyState message="No team members found for this filter." ctaLabel="Clear department" ctaTo={undefined} />
      )}

      {!isLoading && !isError && team.length > 0 && (
        <div className="lr-table-wrap">
          <table className="lr-table">
            <caption className="sr-only">Team attendance for {month}</caption>
            <thead>
              <tr>
                <th scope="col">Employee</th><th scope="col">Role</th>
                <th scope="col">Working days</th><th scope="col">Approved</th>
                <th scope="col">Pending</th><th scope="col">Attendance</th>
                <th scope="col">By type</th>
              </tr>
            </thead>
            <tbody>
              {team.map((row) => (
                <tr key={row.user.id}>
                  <td>{row.user.full_name}</td>
                  <td style={{ textTransform: 'capitalize' }}>{row.user.role}</td>
                  <td>{row.working_days}</td>
                  <td>{days(row.approved_days)}</td>
                  <td>{days(row.pending_days)}</td>
                  <td><AttendanceIndicator percentage={row.attendance_percentage} /></td>
                  <td>
                    <div className="lr-chip-row">
                      {Object.entries(row.by_type || {}).map(([code, count]) => (
                        <LeaveTypeChip key={code} leaveType={code} count={count} />
                      ))}
                      {Object.keys(row.by_type || {}).length === 0 && <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TeamAttendance;
