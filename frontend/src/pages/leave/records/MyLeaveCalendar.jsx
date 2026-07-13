import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '../../../hooks/useAuth';
import { useCalendar, useHolidays } from '../../../hooks/useLeaveRecords';
import { monthName, days } from '../../../utils/leaveFormat';
import CalendarDay from '../../../components/leave-records/CalendarDay';
import { Skeleton, ErrorState } from '../../../components/leave-records/States';

const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const toISO = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
// Nepal's weekly holiday is Saturday only (Sunday is a working day).
const isWeekend = (d) => d.getDay() === 6;

/** Monday-aligned grid of 42 days covering the given month. */
const buildGrid = (year, month) => {
  const first = new Date(year, month, 1);
  const offset = (first.getDay() + 6) % 7; // 0 = Monday
  const start = new Date(year, month, 1 - offset);
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
};

const MyLeaveCalendar = () => {
  const { role } = useAuth();
  const isManager = ['approver', 'admin', 'checker'].includes(role);
  const today = new Date();
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() });
  const [selected, setSelected] = useState(null);
  const [showTeam, setShowTeam] = useState(false);

  const grid = useMemo(() => buildGrid(cursor.year, cursor.month), [cursor]);
  const gridStart = toISO(grid[0]);
  const gridEnd = toISO(grid[grid.length - 1]);

  const { data: records = [], isLoading, isError, error, refetch } = useCalendar(gridStart, gridEnd);
  const { data: holidays = [] } = useHolidays(cursor.year);

  const recordByDate = useMemo(() => {
    const map = {};
    for (const r of records) map[r.date] = r;
    return map;
  }, [records]);
  const holidayByDate = useMemo(() => {
    const map = {};
    for (const h of holidays) map[h.date] = h;
    return map;
  }, [holidays]);

  const move = (delta) => setCursor((c) => {
    const d = new Date(c.year, c.month + delta, 1);
    return { year: d.getFullYear(), month: d.getMonth() };
  });

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <div className="lr-page-head">
        <div>
          <h2>My Calendar</h2>
          <div className="lr-page-sub">Your leave days, weekends and holidays at a glance</div>
        </div>
        {isManager && (
          <button
            type="button"
            className={`lr-tab ${showTeam ? 'on' : ''}`}
            aria-pressed={showTeam}
            onClick={() => setShowTeam((s) => !s)}
          >
            Show team
          </button>
        )}
      </div>

      {showTeam && (
        <div className="lr-chart-card" role="note" style={{ marginTop: 0 }}>
          Per-day team overlay is available on the <a href="/leave/calendar">Team Calendar</a> and
          {' '}<a href="/leaves/team-attendance">Team Attendance</a> pages.
        </div>
      )}

      {isError && <ErrorState error={error} onRetry={refetch} />}
      {isLoading && !isError && <Skeleton rows={1} height={420} />}

      {!isLoading && !isError && (
        <div className="lr-cal">
          <div className="lr-cal-toolbar">
            <div className="lr-cal-title">{monthName(cursor.month + 1)} {cursor.year}</div>
            <div className="lr-cal-nav">
              <button type="button" className="lr-btn lr-btn-ghost" aria-label="Previous month" onClick={() => move(-1)}><ChevronLeft size={16} /></button>
              <button type="button" className="lr-btn lr-btn-ghost" onClick={() => setCursor({ year: today.getFullYear(), month: today.getMonth() })}>Today</button>
              <button type="button" className="lr-btn lr-btn-ghost" aria-label="Next month" onClick={() => move(1)}><ChevronRight size={16} /></button>
            </div>
          </div>

          <div className="lr-cal-grid" role="grid" aria-label={`Leave calendar for ${monthName(cursor.month + 1)} ${cursor.year}`}>
            {DOW.map((d) => <div key={d} className={`lr-cal-dow ${d === 'Sat' ? 'is-saturday' : ''}`} role="columnheader">{d}</div>)}
            {grid.map((d) => {
              const iso = toISO(d);
              return (
                <CalendarDay
                  key={iso}
                  date={d}
                  inMonth={d.getMonth() === cursor.month}
                  record={recordByDate[iso]}
                  isWeekend={isWeekend(d)}
                  isHoliday={Boolean(holidayByDate[iso])}
                  holidayName={holidayByDate[iso]?.name}
                  onSelect={setSelected}
                />
              );
            })}
          </div>

          <div className="lr-cal-legend">
            <span><span className="lr-cal-badge" style={{ position: 'static' }}>H</span> Holiday</span>
            <span><span style={{ width: 12, height: 12, background: 'var(--bg-main)', border: '1px solid var(--border)', display: 'inline-block', borderRadius: 3 }} /> Weekend</span>
            <span>Coloured tag = leave type (code shown for colour-blind support)</span>
          </div>
        </div>
      )}

      {selected && (
        <div className="lr-modal-overlay" role="dialog" aria-modal="true" aria-label="Leave day details" onClick={() => setSelected(null)}>
          <div className="lr-modal" onClick={(e) => e.stopPropagation()}>
            <div className="lr-modal-head">
              <h3>{selected.date}</h3>
              <button type="button" className="lr-modal-close" aria-label="Close" onClick={() => setSelected(null)}>×</button>
            </div>
            <dl className="lr-modal-grid">
              <div><dt>Type</dt><dd>{selected.leave_type_code}</dd></div>
              <div><dt>Status</dt><dd style={{ textTransform: 'capitalize' }}>{selected.status}</dd></div>
              <div><dt>Portion</dt><dd>{selected.day_portion.replace('_', ' ')}</dd></div>
              <div><dt>Counts as</dt><dd>{days(selected.portion_days)} day</dd></div>
            </dl>
          </div>
        </div>
      )}
    </div>
  );
};

export default MyLeaveCalendar;
