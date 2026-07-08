import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaves } from '../../hooks/useLeaves';
import { useAuth } from '../../hooks/useAuth';
import { adminService } from '../../services/adminService';
import { Calendar, Clock, User, FileText, ArrowLeft, Send } from 'lucide-react';

const ApplyLeave = () => {
  const navigate = useNavigate();
  const { applyLeave, loading } = useLeaves();
  const { role } = useAuth();
  const [managers, setManagers] = useState([]);

  useEffect(() => {
    const fetchManagers = async () => {
      try {
        const users = await adminService.getUsers();
        const approvers = users.filter(u => u.role === 'approver');
        setManagers(approvers);
      } catch (err) {
        console.error('Error fetching users:', err);
      }
    };
    fetchManagers();
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

  if (role !== 'maker' && role !== 'admin') {
    return (
      <div className="page">
        <div className="pg-head">
          <div>
            <div className="pg-title">Access Denied</div>
            <div className="pg-desc">Only makers may apply for leave.</div>
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

  const handleSubmit = async () => {
    setError(null);
    
    if (!formData.start || !formData.end || !formData.manager || !formData.reason) {
      setError('Please fill all required fields');
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
      setError(err?.response?.data?.detail || err.message || 'Failed to submit application');
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
              <option>Annual Leave</option>
              <option>Sick Leave</option>
              <option>Casual Leave</option>
              <option>Unpaid Leave</option>
              <option>Work from Home</option>
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
              <select id="lv-manager" value={formData.manager} onChange={(e) => {
                const selectedId = e.target.value;
                const selected = managers.find(m => m.id === selectedId);
                const name = selected ? `${selected.first_name} ${selected.last_name}`.trim() || selected.username || selected.email : '';
                setFormData({ ...formData, manager: name, approver_id: selectedId });
              }}>
                <option value="">Select Manager</option>
                {managers.map(m => {
                  const name = m.first_name && m.last_name ? `${m.first_name} ${m.last_name}` : m.username || m.email;
                  const roleLabel = m.role === 'approver' ? 'Approver' : m.role;
                  return (
                    <option key={m.id} value={m.id}>
                      {name} — {roleLabel}
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
