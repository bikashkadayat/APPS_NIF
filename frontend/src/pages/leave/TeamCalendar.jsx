import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaves } from '../../hooks/useLeaves';
import { useAutoRefresh } from '../../hooks/useAutoRefresh';
import LeaveCard from '../../components/common/LeaveCard';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';

const TeamCalendar = () => {
  const navigate = useNavigate();
  const { leaves, loading, error, fetchLeaves } = useLeaves();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState(null);

  useEffect(() => {
    fetchLeaves();
  }, [fetchLeaves]);
  useAutoRefresh(fetchLeaves, 30000); // team leave updates appear without a refresh

  // Calendar logic
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstDayOfMonth = new Date(year, month, 1).getDay(); // 0 is Sunday
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();

  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  // Helper to map events
  const getEventsForDay = (day) => {
    return leaves.filter(l => {
      const start = new Date(l.start);
      const end = new Date(l.end);
      const curr = new Date(year, month, day);
      return curr >= start && curr <= end;
    });
  };

  const goToToday = () => setCurrentDate(new Date());
  const goToPrevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const goToNextMonth = () => setCurrentDate(new Date(year, month + 1, 1));

  // Generate blank spaces before first day
  const blanks = Array.from({ length: firstDayOfMonth }).map((_, i) => (
    <div key={`blank-${i}`} className="cal-day empty"></div>
  ));

  const days = Array.from({ length: daysInMonth }).map((_, i) => {
    const day = i + 1;
    const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
    const isSaturday = new Date(year, month, day).getDay() === 6; // Nepal weekly holiday
    const dayEvents = getEventsForDay(day);

    return (
      <div key={`day-${day}`} className={`cal-day ${isToday ? 'today' : ''} ${isSaturday ? 'is-saturday' : ''}`}>
        <span className="cal-date">{day}</span>
        {isSaturday && <span className="cal-holiday-tag">Holiday</span>}
        <div className="cal-events">
          {dayEvents.slice(0, 3).map(ev => (
            <div key={`${ev.id}-${day}`} className={`cal-event ${ev.status}`} onClick={() => setSelectedEvent(ev)}>
              {ev.employee.split(' ')[0]} - {ev.type}
            </div>
          ))}
          {dayEvents.length > 3 && (
            <div className="cal-more">+{dayEvents.length - 3} more</div>
          )}
        </div>
      </div>
    );
  });

  return (
    <div className="page">
      <div className="pg-head">
        <div className="pg-head-left">
          <div className="pg-breadcrumb">
            <button className="pg-back" onClick={() => navigate('/leave')}>
              <ArrowLeft size={18} />
            </button>
            Leave Management
          </div>
          <div className="pg-title">Team Calendar</div>
          <div className="pg-desc">View team leave schedules and plan accordingly</div>
        </div>
        <div className="pg-head-right">
          <div className="pg-logo">
            <img src="/NIF.png" alt="NIF Logo" />
          </div>
        </div>
      </div>

      <div className="table-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn btn-ghost btn-sm" onClick={goToPrevMonth}>
              <ChevronLeft size={18} />
            </button>
            <h3 style={{ fontFamily: '"Playfair Display", serif', fontSize: '20px', fontWeight: 700, minWidth: '130px', textAlign: 'center' }}>
              {monthNames[month]} {year}
            </h3>
            <button className="btn btn-ghost btn-sm" onClick={goToNextMonth}>
              <ChevronRight size={18} />
            </button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn btn-ghost btn-sm" onClick={goToToday}>Today</button>
            <div className="calendar-legend">
              <span className="legend-item">
                <span className="legend-color pending"></span> Pending
              </span>
              <span className="legend-item">
                <span className="legend-color approved"></span> Approved
              </span>
            </div>
          </div>
        </div>

        {loading && <div style={{ padding: '4px 0 12px', color: 'var(--text-muted)', fontSize: 13 }}>Loading team leave…</div>}
        {error && (
          <div style={{ padding: '10px 14px', marginBottom: 12, borderRadius: 8, background: 'rgba(220,38,38,.08)', color: '#b91c1c', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span>Could not load team leave data. {error}</span>
            <button className="btn btn-ghost btn-sm" onClick={fetchLeaves}>Retry</button>
          </div>
        )}

        <div className="calendar-container">
          <div className="calendar-header">
            <div className="calendar-title">
              {monthNames[month]} {year}
            </div>
            <div className="calendar-legend">
              <span className="legend-item">
                <span className="legend-color pending"></span> Pending
              </span>
              <span className="legend-item">
                <span className="legend-color approved"></span> Approved
              </span>
              <span className="legend-item">
                <span className="legend-color today"></span> Today
              </span>
            </div>
          </div>

          <div className="calendar-grid">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(h => (
              <div key={h} className={`cal-day header ${h === 'Sat' ? 'is-saturday' : ''}`}>{h}</div>
            ))}
            {blanks}
            {days}
          </div>
        </div>
      </div>

      {selectedEvent && (
        <div className="modal-overlay" onClick={() => setSelectedEvent(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Leave Details</h3>
            <LeaveCard leave={selectedEvent} />
            <button className="btn btn-primary" onClick={() => setSelectedEvent(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamCalendar;
