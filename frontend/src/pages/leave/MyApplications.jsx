import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaves } from '../../hooks/useLeaves';
import { useAuth } from '../../hooks/useAuth';
import Badge from '../../components/common/Badge';
import LeaveDocActions from '../../components/documents/LeaveDocActions';
import { ArrowLeft, Plus } from 'lucide-react';

const MyApplications = () => {
  const navigate = useNavigate();
  const { leaves, loading, fetchLeaves } = useLeaves();
  const { user, role } = useAuth();
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchLeaves();
  }, [fetchLeaves]);

  // Prevent approvers from accessing this page
  if (role === 'approver') {
    return (
      <div className="page">
        <div className="pg-head">
          <div className="pg-head-left">
            <div className="pg-breadcrumb">
              <button className="pg-back" onClick={() => navigate(-1)}>
                <ArrowLeft size={18} />
              </button>
              Leave Management
            </div>
            <div className="pg-title">Access Denied</div>
            <div className="pg-desc">Approvers cannot view their own applications.</div>
          </div>
          <div className="pg-head-right">
            <div className="pg-logo">
              <img src="/NIF.png" alt="NIF Logo" />
            </div>
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

  const myLeaves = leaves.filter(l => l.employee === user.name && (filter === 'all' || l.status === filter));

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
          <div className="pg-title">My Applications</div>
          <div className="pg-desc">Track all your leave applications</div>
        </div>
        <div className="pg-head-right">
          <div className="pg-logo">
            <img src="/NIF.png" alt="NIF Logo" />
          </div>
        </div>
      </div>
      <div className="table-card">
        <div className="tc-top">
          <span className="tc-title">Applications</span>
          <div className="filter-row">
            <button className={`ftag ${filter === 'all' ? 'on' : ''}`} onClick={() => setFilter('all')}>All</button>
            <button className={`ftag ${filter === 'pending' ? 'on' : ''}`} onClick={() => setFilter('pending')}>Pending</button>
            <button className={`ftag ${filter === 'approved' ? 'on' : ''}`} onClick={() => setFilter('approved')}>Approved</button>
            <button className={`ftag ${filter === 'rejected' ? 'on' : ''}`} onClick={() => setFilter('rejected')}>Rejected</button>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '24px', textAlign: 'center' }}>Loading applications...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Leave Details</th>
                <th>Dates</th>
                <th>Status</th>
                <th>Documents</th>
              </tr>
            </thead>
            <tbody>
              {myLeaves.map(leave => (
                <tr key={leave.id} className="mrow">
                  <td>
                    <div className="ref-no">{leave.id}</div>
                    <div className="leave-meta">{leave.applied}</div>
                  </td>
                  <td>
                    <div className="leave-title">{leave.type}</div>
                    <div className="leave-meta">{leave.reason}</div>
                  </td>
                  <td>
                    <div style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{leave.start} to {leave.end}</div>
                    <div className="leave-meta">{leave.days} Days</div>
                  </td>
                  <td>
                    <Badge status={leave.status} />
                  </td>
                  <td>
                    {leave.status === 'approved'
                      ? <LeaveDocActions leaveId={leave.id} />
                      : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Available when approved</span>}
                  </td>
                </tr>
              ))}
              {myLeaves.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
                    No applications found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default MyApplications;
