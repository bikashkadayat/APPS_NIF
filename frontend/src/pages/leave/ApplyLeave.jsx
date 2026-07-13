import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaves } from '../../hooks/useLeaves';
import { useAuth } from '../../hooks/useAuth';
import { adminService } from '../../services/adminService';
import { leaveService, leaveTypeLabel } from '../../services/leaveService';
import { roleLabel, can } from '../../services/roles';
import { Calendar, Clock, User, FileText, ArrowLeft, Send } from 'lucide-react';

const ApplyLeave = () => {
  const navigate = useNavigate();
  const { applyLeave, loading } = useLeaves();
  const { role } = useAuth();
  const [managers, setManagers] = useState([]);
  // Leave types this user's category may apply for (from the entitlement engine).
  const [leaveTypes, setLeaveTypes] = useState([]);

  useEffect(() => {
    const fetchManagers = async () => {
      try {
        const users = await adminService.getUsers();
        // Reporting managers = Department Heads (checker) and HR (approver).
        const mgrs = users.filter(u => ['approver', 'checker'].includes(u.role) && u.is_active !== false);
        setManagers(mgrs);
      } catch (err) {
        console.error('Error fetching users:', err);
      }
    };
    const fetchTypes = async () => {
      try {
        const ent = await leaveService.getEntitlements();
        // applicable_types are uppercase codes (ANNUAL, SICK, COMPENSATORY, …).
        const labels = (ent.applicable_types || []).map((c) => leaveTypeLabel(c.toLowerCase()));
        setLeaveTypes(labels);
      } catch {
        setLeaveTypes(['Annual Leave', 'Sick Leave']); // safe fallback
      }
    };
    fetchManagers();
    fetchTypes();
  }, []);

  const [formData, setFormData] = useState({
    type: 'Annual Leave',
    priority: 'Normal',
    start: '',
    end: '',
    manager: '',
    approver_id: '',
    contact: '',
    reason: '',
    handover: ''
  });
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  // Keep the selected type valid for the user's category (default to the first).
  useEffect(() => {
    if (leaveTypes.length && !leaveTypes.includes(formData.type)) {
      setFormData((f) => ({ ...f, type: leaveTypes[0] }));
    }
  }, [leaveTypes]); // eslint-disable-line react-hooks/exhaustive-deps

  // Employees, Department Heads and HR may apply for their own leave; Admin is an
  // oversight role and cannot (backend also 403s admins). Central gate = roles.js.
  if (!can(role, 'applyLeave')) {
    return (
      <div className="page">
        <div className="pg-head">
          <div>
            <div className="pg-title">Access Denied</div>
            <div className="pg-desc">Admins manage and approve leave and do not submit personal applications.</div>
          </div>
        </div>
        <div className="empty-state">
          <div className="empty-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          </div>
          <div className="empty-msg">You do not have permission to view this page.</div>
        </div>
      </div>
    );
  }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.id.replace('lv-', '')]: e.target.value });
  };

  const showSuccess = (message) => {
    setSuccessMessage(message);
    window.setTimeout(() => setSuccessMessage(''), 3500);
  };

  const extractError = (err) => {
    const data = err?.response?.data;
    if (!data) return err?.message || 'Failed to submit application';
    if (Array.isArray(data)) return data.join(' ');
    if (typeof data === 'string') return data;
    if (data.detail) return data.detail;
    if (typeof data === 'object') {
      // DRF field errors: {"field": ["msg", ...], ...}
      const parts = Object.entries(data).map(([k, v]) => {
        const val = Array.isArray(v) ? v.join(' ') : v;
        return k === 'non_field_errors' ? val : `${k}: ${val}`;
      });
      if (parts.length) return parts.join(' \n');
    }
    return err?.message || 'Failed to submit application';
  };

  const handleSubmit = async () => {
    setError(null);

    if (!formData.start || !formData.end || !formData.approver_id || !formData.reason) {
      setError('Please fill all required fields, including Reporting Manager.');
      return;
    }

    if (new Date(formData.end) < new Date(formData.start)) {
      setError('End date must be after start date');
      return;
    }

    try {
      await applyLeave(formData);
      showSuccess('Leave application submitted successfully!');
      setTimeout(() => navigate('/leave/my-applications'), 1500);
    } catch (err) {
      setError(extractError(err));
    }
  };

  return (
    <div className="page">
      {(error || successMessage) && (
        <div className="popup-overlay" onClick={() => { setError(null); setSuccessMessage(''); }}>
          <div className="popup-modal" onClick={e => e.stopPropagation()}>
            {error && (
              <>
                <div className="popup-icon popup-error-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                </div>
                <h3>Submission Failed</h3>
                <p>{error}</p>
              </>
            )}
            {successMessage && (
              <>
                <div className="popup-icon popup-success-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                </div>
                <h3>Application Submitted</h3>
                <p>{successMessage}</p>
              </>
            )}
            <button className="popup-btn" onClick={() => { setError(null); setSuccessMessage(''); }}>OK</button>
          </div>
        </div>
      )}

      <div className="pg-head">
        <div className="pg-head-left">
          <div className="pg-breadcrumb">
            <button className="pg-back" onClick={() => navigate(-1)}>
              <ArrowLeft size={18} />
            </button>
            Leave Management
          </div>
          <div className="pg-title">Apply for Leave</div>
          <div className="pg-desc">Submit a new leave application for approval</div>
        </div>
        <div className="pg-head-right">
          <div className="pg-logo">
            <img src="/NIF.png" alt="NIF Logo" />
          </div>
        </div>
      </div>

      <div className="table-card" style={{ padding: '24px' }}>
        <div className="fgrid">
          <div className="fg">
            <label><Calendar size={16} /> Leave Type <span className="req">*</span></label>
            <select id="lv-type" value={formData.type} onChange={handleChange}>
              {leaveTypes.length === 0 && <option value="">No leave types available for your category</option>}
              {leaveTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="fg">
            <label><Clock size={16} /> Priority</label>
            <select id="lv-priority" value={formData.priority} onChange={handleChange}>
              <option>Normal</option>
              <option>Urgent</option>
            </select>
          </div>
        </div>
        <div className="fgrid">
          <div className="fg">
            <label><Calendar size={16} /> Start Date <span className="req">*</span></label>
            <input type="date" id="lv-start" value={formData.start} onChange={handleChange} />
          </div>
          <div className="fg">
            <label><Calendar size={16} /> End Date <span className="req">*</span></label>
            <input type="date" id="lv-end" value={formData.end} onChange={handleChange} />
          </div>
        </div>
        <div className="fgrid">
          <div className="fg">
            <label><User size={16} /> Reporting Manager <span className="req">*</span></label>
              <select id="lv-manager" value={formData.approver_id} onChange={(e) => {
                const selectedId = e.target.value;
                const selected = managers.find(m => m.id === selectedId);
                const name = selected ? (`${selected.first_name || ''} ${selected.last_name || ''}`.trim() || selected.username || selected.email) : '';
                setFormData({ ...formData, manager: name, approver_id: selectedId });
              }}>
                <option value="">Select Manager</option>
                {managers.map(m => {
                  const name = m.first_name && m.last_name ? `${m.first_name} ${m.last_name}` : m.username || m.email;
                  return (
                    <option key={m.id} value={m.id}>
                      {name} — {roleLabel(m.role)}
                    </option>
                  );
                })}
              </select>
          </div>
          <div className="fg">
            <label><User size={16} /> Contact During Leave</label>
            <input type="text" id="lv-contact" placeholder="Phone or email" value={formData.contact} onChange={handleChange} />
          </div>
        </div>
        <div className="fg">
          <label><FileText size={16} /> Reason for Leave <span className="req">*</span></label>
          <textarea id="lv-reason" placeholder="Provide detailed reason for your leave application..." value={formData.reason} onChange={handleChange}></textarea>
        </div>
        <div className="fg">
          <label><FileText size={16} /> Work Handover Notes</label>
          <textarea id="lv-handover" placeholder="Describe any pending tasks or handover instructions..." style={{ minHeight: '60px' }} value={formData.handover} onChange={handleChange}></textarea>
        </div>
        <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
          <button className="btn btn-ghost" onClick={() => navigate(-1)} disabled={loading}>
            <ArrowLeft size={16} /> Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Submitting...' : <>Submit Application <Send size={16} /></>}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApplyLeave;
