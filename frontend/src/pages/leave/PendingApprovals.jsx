import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaves } from '../../hooks/useLeaves';
import { useAuth } from '../../hooks/useAuth';
import Badge from '../../components/common/Badge';
import LeaveReviewModal from '../../components/leave/LeaveReviewModal';
import { ArrowLeft, Eye } from 'lucide-react';

const PendingApprovals = () => {
  const navigate = useNavigate();
  const { leaves, loading, error, fetchLeaves } = useLeaves();
  const { role } = useAuth();
  const [popup, setPopup] = useState(null);
  const [reviewId, setReviewId] = useState(null);

  useEffect(() => {
    fetchLeaves();
  }, [fetchLeaves]);

  // Both review stages can decide from this screen: Dept Head (checker) acts on
  // Level-1 'pending' items, HR (approver) acts on Level-2 'pending_hr' items,
  // Admin oversees both. The modal routes each decision to the right endpoint.
  const canApprove = ['checker', 'approver', 'admin'].includes(role);
  const canReview = ['approver', 'checker', 'admin'].includes(role);

  if (!canReview) {
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
            <div className="pg-desc">Only reviewers may view pending leave requests.</div>
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

  // Show the queue that matches the reviewer's stage. HR's queue is the
  // 'pending_hr' items (Dept Head already approved) - previously this filtered
  // only 'pending', so HR saw an empty queue and could never approve (H1).
  const stageStatuses = role === 'checker' ? ['pending']
    : role === 'approver' ? ['pending_hr']
    : ['pending', 'pending_hr']; // admin oversees both stages
  const pendingLeaves = leaves.filter(l => stageStatuses.includes(l.status));

  const handleDecided = (status) => {
    setReviewId(null);
    fetchLeaves();
    setPopup(status === 'approved'
      ? { type: 'success', title: 'Application Approved', message: 'Leave request has been approved.' }
      : { type: 'success', title: 'Application Rejected', message: 'Leave request has been rejected.' });
  };

  return (
    <div className="page">
      {popup && (
        <div className="popup-overlay" onClick={() => setPopup(null)}>
          <div className="popup-modal" onClick={e => e.stopPropagation()}>
            <div className={`popup-icon ${popup.type === 'success' ? 'popup-success-icon' : 'popup-error-icon'}`}>
              {popup.type === 'success' ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              )}
            </div>
            <h3>{popup.title}</h3>
            <p>{popup.message}</p>
            <button className="popup-btn" onClick={() => setPopup(null)}>OK</button>
          </div>
        </div>
      )}

      <div className="pg-head">
        <div className="pg-head-left">
          <div className="pg-breadcrumb">
            <button className="pg-back" onClick={() => navigate('/leave')}>
              <ArrowLeft size={18} />
            </button>
            Leave Management
          </div>
          <div className="pg-title">Pending Approvals</div>
          <div className="pg-desc">Review and approve team leave applications</div>
        </div>
        <div className="pg-head-right">
          <div className="pg-logo">
            <img src="/NIF.png" alt="NIF Logo" />
          </div>
        </div>
      </div>
      
      {loading ? (
        <div>Loading pending items...</div>
      ) : error ? (
        <div className="empty-state">
          <div className="empty-msg" style={{ color: 'var(--danger, #b91c1c)' }}>Could not load pending requests. {error}</div>
          <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={fetchLeaves}>Retry</button>
        </div>
      ) : pendingLeaves.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">✓</div>
          <div className="empty-msg">You have no pending approvals.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px'}}>
          {pendingLeaves.map(leave => (
            <div key={leave.id} style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 'var(--r2)', padding: '20px', boxShadow: 'var(--shadow)'}}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid var(--border-light)', paddingBottom: '16px'}}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px'}}>
                   <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--nepal-blue)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                    {(leave.employee || '?').substring(0,2).toUpperCase()}
                   </div>
                   <div>
                     <div style={{ fontWeight: 600, fontSize: '15px'}}>{leave.employee}</div>
                     <div style={{ fontSize: '12px', color: 'var(--text-muted)'}}>{leave.type} • Applied on {leave.applied}</div>
                   </div>
                </div>
                <div><Badge status={leave.status} /></div>
              </div>
              
              <div style={{ fontSize: '13px', marginBottom: '20px'}}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '12px'}}>
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px'}}>Dates</div>
                    <div>{leave.start} to {leave.end} <span style={{ color: 'var(--text-muted)' }}>({leave.days} days)</span></div>
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px'}}>Reason</div>
                    <div>{leave.reason || '-'}</div>
                  </div>
                </div>
                {leave.handover_notes && (
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px'}}>Work Handover Notes</div>
                    <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', fontSize: '13px', lineHeight: 1.5 }}>{leave.handover_notes}</div>
                  </div>
                )}
              </div>
              
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', borderTop: '1px solid var(--border-light)', paddingTop: '16px'}}>
                <button className="btn btn-primary" onClick={() => setReviewId(leave.id)}>
                  <Eye size={16} /> Review &amp; Decide
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {reviewId && (
        <LeaveReviewModal
          leaveId={reviewId}
          canApprove={canApprove}
          onClose={() => setReviewId(null)}
          onDecided={handleDecided}
        />
      )}
    </div>
  );
};

export default PendingApprovals;
