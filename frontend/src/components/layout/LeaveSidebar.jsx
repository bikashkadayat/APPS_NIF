import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { can } from '../../services/roles';

const LeaveSidebar = ({ open = false, onClose }) => {
  const { role } = useAuth();
  // Close the drawer whenever a nav link is activated (event delegation, so no
  // per-link wiring). Harmless on desktop where the drawer is always in-flow.
  const handleNavClick = (e) => {
    if (e.target.closest('a.sb-item')) onClose?.();
  };
  // Personal self-service actions — Admin is oversight-only (excluded).
  const canApply = can(role, 'applyLeave');
  const canViewOwnApplications = can(role, 'myApplications');
  const canCreateMemo = can(role, 'createMemo');
  const canViewOwnMemos = can(role, 'myMemos');
  const canReview = ['approver', 'checker', 'admin'].includes(role);
  const canCheck = role === 'checker' || role === 'admin';
  // Managers / HR see the Team Records section.
  const isManager = role === 'admin' || role === 'approver';
  const isAdmin = role === 'admin';

  return (
    <nav
      id="app-sidebar"
      className={`sidebar ${open ? 'open' : ''}`}
      role="navigation"
      aria-label="Main navigation"
      onClick={handleNavClick}
    >
      {/* Mobile-only close button (CSS hides it on desktop). */}
      <button type="button" className="sb-close" aria-label="Close menu" onClick={onClose}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
      <div className="sb-section">
        <div className="sb-hd">Overview</div>
        <NavLink to="/leave" end className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
          <span className="sb-ico">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          </span>
          Dashboard
        </NavLink>
      </div>

      <div className="sb-section">
        <div className="sb-hd">Leave Management</div>
        {canApply && (
          <NavLink to="/leave/apply" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
            </span>
            Apply for Leave
          </NavLink>
        )}
        {canViewOwnApplications && (
          <NavLink to="/leave/my-applications" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>
            </span>
            My Applications
          </NavLink>
        )}
        {canReview && (
          <NavLink to="/leave/pending" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            </span>
            {canCheck ? 'Review Requests' : 'Pending Requests'}
          </NavLink>
        )}
      </div>

      <div className="sb-section">
        <div className="sb-hd">Memos</div>
        {canCreateMemo && (
          <NavLink to="/memos/create" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg></span>
            Create Memo
          </NavLink>
        )}
        {canViewOwnMemos && (
          <NavLink to="/memos/my" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></span>
            My Memos
          </NavLink>
        )}
        <NavLink to="/memos" end className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
          <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg></span>
          All Memos
        </NavLink>
        {(role === 'checker' || role === 'admin') && (
          <NavLink to="/memos/pending-reviews" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></span>
            Pending Reviews
          </NavLink>
        )}
        {(role === 'approver' || role === 'admin') && (
          <NavLink to="/memos/pending-approvals" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg></span>
            Pending Approvals
          </NavLink>
        )}
      </div>

      <div className="sb-section">
        <div className="sb-hd">My Records</div>
        <NavLink to="/leaves/my-history" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
          <span className="sb-ico">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M7 14l3-3 3 3 5-5"/></svg>
          </span>
          My History
        </NavLink>
        <NavLink to="/leaves/my-calendar" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
          <span className="sb-ico">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
          </span>
          My Calendar
        </NavLink>
        <NavLink to="/leaves/weekly-report" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
          <span className="sb-ico">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><rect x="7" y="10" width="3" height="7"/><rect x="14" y="6" width="3" height="11"/></svg>
          </span>
          Weekly Report
        </NavLink>
        <NavLink to="/leaves/monthly-report" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
          <span className="sb-ico">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M19 9l-5 5-4-4-3 3"/></svg>
          </span>
          Monthly Report
        </NavLink>
      </div>

      <div className="sb-section">
        <div className="sb-hd">Team</div>
        <NavLink to="/leave/calendar" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
          <span className="sb-ico">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
          </span>
          Team Calendar
        </NavLink>
      </div>

      {isManager && (
        <div className="sb-section">
          <div className="sb-hd">Team Records</div>
          <NavLink to="/leaves/team-attendance" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>
            </span>
            Team Attendance
          </NavLink>
          <NavLink to="/leave/calendar" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
            </span>
            Team Calendar
          </NavLink>
        </div>
      )}

      {isAdmin && (
        <div className="sb-section">
          <div className="sb-hd">Administration</div>
          <NavLink to="/admin/users" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 11h-6M19 8v6"/></svg></span>
            User Management
          </NavLink>
          <NavLink to="/admin/leaves/employees" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg></span>
            Employees
          </NavLink>
          <NavLink to="/admin/leaves/policies" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></svg></span>
            Policies
          </NavLink>
          <NavLink to="/admin/leaves/holidays" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg></span>
            Holidays
          </NavLink>
          <NavLink to="/admin/leaves/departments" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><path d="M6 10v4a2 2 0 002 2h6"/></svg></span>
            Departments
          </NavLink>
          <NavLink to="/admin/leaves/leave-types" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><circle cx="7" cy="7" r="1"/></svg></span>
            Leave Types
          </NavLink>
          <NavLink to="/admin/leaves/bulk-actions" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg></span>
            Bulk Actions
          </NavLink>
        </div>
      )}

      {(role === 'approver' || role === 'admin') && (
        <div className="sb-section">
          <div className="sb-hd">Attendance</div>
          <NavLink to="/admin/attendance-reports" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M7 14l3-3 3 3 5-5"/></svg></span>
            Attendance Reports
          </NavLink>
        </div>
      )}

      {isAdmin && (
        <div className="sb-section">
          <div className="sb-hd">Reports &amp; Analytics</div>
          <NavLink to="/admin/analytics" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M18 9l-5 5-3-3-4 4"/></svg></span>
            Analytics
          </NavLink>
          <NavLink to="/reports" end className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M9 15h6M9 11h2"/></svg></span>
            Reports
          </NavLink>
          <NavLink to="/reports/history" className={({ isActive }) => `sb-item ${isActive ? 'on' : ''}`}>
            <span className="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 106 5.3L3 8"/><path d="M12 7v5l4 2"/></svg></span>
            Report History
          </NavLink>
        </div>
      )}
    </nav>
  );
};

export default LeaveSidebar;
