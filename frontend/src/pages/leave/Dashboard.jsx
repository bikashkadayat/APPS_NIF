import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLeaves } from '../../hooks/useLeaves';
import { useAuth } from '../../hooks/useAuth';
import LeaveCard from '../../components/common/LeaveCard';
import DashboardRecordsSummary from '../../components/leave-records/DashboardRecordsSummary';
import { CalendarDays, Stethoscope, Briefcase, Plane, Plus, ArrowRight, ClipboardCheck, Users, Calendar, FileText, CheckCircle, Clock, XCircle } from 'lucide-react';

const LeaveDashboard = () => {
  const navigate = useNavigate();
  const { leaves, balances, loading, fetchLeaves, fetchBalances } = useLeaves();
  const { role, user } = useAuth();
  const [showWelcome, setShowWelcome] = useState(() => {
    const justLoggedIn = localStorage.getItem('justLoggedIn');
    if (justLoggedIn) {
      localStorage.removeItem('justLoggedIn');
      return true;
    }
    return false;
  });

  useEffect(() => {
    if (showWelcome) {
      const timer = setTimeout(() => setShowWelcome(false), 4000);
      return () => clearTimeout(timer);
    }
  }, [showWelcome]);

  useEffect(() => {
    fetchLeaves();
    if (role !== 'approver') {
      fetchBalances();
    }
  }, [fetchLeaves, fetchBalances, role]);

  const stats = {
    total: leaves.length,
    pending: leaves.filter(l => l.status === 'pending').length,
    approved: leaves.filter(l => l.status === 'approved').length,
    rejected: leaves.filter(l => l.status === 'rejected').length
  };

  const getBalance = (type) => {
    const balance = balances.find(b => b.leave_type === type);
    return balance || { total_allocated: 0, used_so_far: 0, remaining: 0 };
  };

  const recent = leaves.slice(0, 4);

  if (role === 'checker' || role === 'approver' || role === 'admin') {
    return (
      <div className="page" style={{ paddingBottom: '80px' }}>
        {showWelcome && (
          <div className="toast-notification">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span>Login successful! Welcome, {user?.name || 'User'}</span>
          </div>
        )}

        <div className="pg-head">
          <div className="pg-head-left">
            <div className="pg-breadcrumb">Leave Management</div>
            <div className="pg-title">Approval Dashboard</div>
            <div className="pg-desc">Review and manage team leave applications</div>
          </div>
          <div className="pg-head-right">
            <div className="pg-logo">
              <img src="/NIF.png" alt="NIF Logo" />
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', marginBottom: '32px' }}>
          <div className="side-card" style={{ padding: '24px', cursor: 'pointer' }} onClick={() => navigate('/leave/pending')}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'var(--warning-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Clock size={24} color="var(--warning)" />
              </div>
              <div>
                <div style={{ fontSize: '28px', fontFamily: '"Playfair Display", serif', fontWeight: 700, color: 'var(--warning)', lineHeight: 1 }}>{stats.pending}</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginTop: '4px' }}>Pending Approvals</div>
              </div>
            </div>
          </div>

          <div className="side-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'var(--success-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <CheckCircle size={24} color="var(--success)" />
              </div>
              <div>
                <div style={{ fontSize: '28px', fontFamily: '"Playfair Display", serif', fontWeight: 700, color: 'var(--success)', lineHeight: 1 }}>{stats.approved}</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginTop: '4px' }}>Approved</div>
              </div>
            </div>
          </div>

          <div className="side-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'var(--danger-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <XCircle size={24} color="var(--danger)" />
              </div>
              <div>
                <div style={{ fontSize: '28px', fontFamily: '"Playfair Display", serif', fontWeight: 700, color: 'var(--danger)', lineHeight: 1 }}>{stats.rejected}</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginTop: '4px' }}>Rejected</div>
              </div>
            </div>
          </div>
        </div>

        <div className="table-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: '"Playfair Display", serif' }}>What You Can Do</h3>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
            <div style={{ padding: '24px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', transition: 'all 0.2s', cursor: 'pointer' }} onClick={() => navigate('/leave/pending')}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--brand-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <ClipboardCheck size={20} color="white" />
                </div>
                <div style={{ fontWeight: 600, fontSize: '16px' }}>Review Pending Requests</div>
              </div>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                View and process leave applications submitted by makers. Approve or reject based on team capacity and policies.
              </div>
            </div>

            <div style={{ padding: '24px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', transition: 'all 0.2s', cursor: 'pointer' }} onClick={() => navigate('/leave/calendar')}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Calendar size={20} color="white" />
                </div>
                <div style={{ fontWeight: 600, fontSize: '16px' }}>View Team Calendar</div>
              </div>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                See who's out on which dates. Plan team activities and ensure coverage during absences.
              </div>
            </div>

            <div style={{ padding: '24px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', transition: 'all 0.2s', cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--draft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Users size={20} color="white" />
                </div>
                <div style={{ fontWeight: 600, fontSize: '16px' }}>View Employee Information</div>
              </div>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Access employee details including leave balances, application history, and contact information.
              </div>
            </div>
          </div>
        </div>

        <div className="table-card" style={{ padding: '24px', marginTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: '"Playfair Display", serif' }}>Recent Applications</h3>
            <button 
              onClick={() => navigate('/leave/pending')}
              style={{ background: 'none', border: 'none', color: 'var(--brand-blue)', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              View all <ArrowRight size={14} />
            </button>
          </div>
          
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading records...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {recent.map(leave => <LeaveCard key={leave.id} leave={leave} />)}
              {recent.length === 0 && <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>No recent applications found.</div>}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="page" style={{ paddingBottom: '80px' }}>
      {showWelcome && (
        <div className="toast-notification">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <span>Login successful! Welcome, {user?.name || 'User'}</span>
        </div>
      )}

      <div className="pg-head">
        <div className="pg-head-left">
          {/* <div className="pg-breadcrumb">Leave Management</div> */}
          <div className="pg-title">My Dashboard</div>
          {/* <div className="pg-desc">Manage your leave applications and track balances</div> */}
        </div>
        <div className="pg-head-right">
          <div className="pg-logo">
            <img src="/NIF.png" alt="NIF Logo" />
          </div>
        </div>
      </div>

      <div className="table-card" style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: '"Playfair Display", serif' }}>What You Can Do</h3>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '24px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', transition: 'all 0.2s', cursor: 'pointer' }} onClick={() => navigate('/leave/apply')}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--brand-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Plus size={20} color="white" />
              </div>
              <div style={{ fontWeight: 600, fontSize: '16px' }}>Apply for Leave</div>
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Submit a new leave request for annual, sick, casual, or other leave types. Your application will be reviewed by your manager.
            </div>
          </div>

          <div style={{ padding: '24px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', transition: 'all 0.2s', cursor: 'pointer' }} onClick={() => navigate('/leave/my-applications')}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--draft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <FileText size={20} color="white" />
              </div>
              <div style={{ fontWeight: 600, fontSize: '16px' }}>View My Applications</div>
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Track the status of your submitted leave applications. See pending, approved, or rejected requests.
            </div>
          </div>

          <div style={{ padding: '24px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', transition: 'all 0.2s', cursor: 'pointer' }} onClick={() => navigate('/leave/calendar')}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Calendar size={20} color="white" />
              </div>
              <div style={{ fontWeight: 600, fontSize: '16px' }}>View Team Calendar</div>
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              See which team members are on leave on specific dates. Plan your time off accordingly.
            </div>
          </div>
        </div>
      </div>

      {/* Phase 6: enterprise leave-records summary (compact) */}
      <DashboardRecordsSummary />

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 340px', gap: '32px' }}>

        {/* MAIN COLUMN */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '40px' }}>
          
          {/* Balances Section */}
          <section>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: '"Playfair Display", serif' }}>My Leave Balances</h3>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
              {/* Annual Leave */}
              {(() => {
                const balance = getBalance('annual');
                const usedPercent = balance.total_allocated > 0 ? (balance.used_so_far / balance.total_allocated) * 100 : 0;
                return (
                  <div className="balance-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div className="bc-type">Annual Leave</div>
                      <CalendarDays size={18} color="var(--brand-blue)" />
                    </div>
                    <div className="bc-used">{balance.used_so_far}</div>
                    <div style={{ background: 'var(--bg-main)', height: '8px', borderRadius: '4px', marginTop: '12px', overflow: 'hidden' }}>
                      <div style={{ background: 'var(--brand-blue)', height: '100%', width: `${usedPercent}%`, borderRadius: '4px' }}></div>
                    </div>
                    <div className="bc-total" style={{ marginTop: '12px' }}>
                      Remaining: <span style={{ fontWeight: 600, color: 'var(--text-primary)'}}>{balance.remaining}</span> / {balance.total_allocated} days
                    </div>
                  </div>
                );
              })()}

              {/* Sick Leave */}
              {(() => {
                const balance = getBalance('sick');
                const usedPercent = balance.total_allocated > 0 ? (balance.used_so_far / balance.total_allocated) * 100 : 0;
                return (
                  <div className="balance-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div className="bc-type">Sick Leave</div>
                      <Stethoscope size={18} color="var(--brand-red)" />
                    </div>
                    <div className="bc-used">{balance.used_so_far}</div>
                    <div style={{ background: 'var(--bg-main)', height: '8px', borderRadius: '4px', marginTop: '12px', overflow: 'hidden' }}>
                      <div style={{ background: 'var(--brand-red)', height: '100%', width: `${usedPercent}%`, borderRadius: '4px' }}></div>
                    </div>
                    <div className="bc-total" style={{ marginTop: '12px' }}>
                      Remaining: <span style={{ fontWeight: 600, color: 'var(--text-primary)'}}>{balance.remaining}</span> / {balance.total_allocated} days
                    </div>
                  </div>
                );
              })()}

              {/* Casual Leave */}
              {(() => {
                const balance = getBalance('casual');
                const usedPercent = balance.total_allocated > 0 ? (balance.used_so_far / balance.total_allocated) * 100 : 0;
                return (
                  <div className="balance-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div className="bc-type">Casual Leave</div>
                      <Briefcase size={18} color="var(--success)" />
                    </div>
                    <div className="bc-used">{balance.used_so_far}</div>
                    <div style={{ background: 'var(--bg-main)', height: '8px', borderRadius: '4px', marginTop: '12px', overflow: 'hidden' }}>
                      <div style={{ background: 'var(--success)', height: '100%', width: `${usedPercent}%`, borderRadius: '4px' }}></div>
                    </div>
                    <div className="bc-total" style={{ marginTop: '12px' }}>
                      Remaining: <span style={{ fontWeight: 600, color: 'var(--text-primary)'}}>{balance.remaining}</span> / {balance.total_allocated} days
                    </div>
                  </div>
                );
              })()}
            </div>
          </section>

          {/* Recent Applications Section */}
          <section>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: '"Playfair Display", serif' }}>Recent Applications</h3>
              <button 
                onClick={() => navigate('/leave/my-applications')}
                style={{ background: 'none', border: 'none', color: 'var(--brand-blue)', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                View full history <ArrowRight size={14} />
              </button>
            </div>
            
            <div className="table-card" style={{ padding: '24px' }}>
              {loading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading records...</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {recent.map(leave => <LeaveCard key={leave.id} leave={leave} />)}
                  {recent.length === 0 && <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>No recent applications found. <button onClick={() => navigate('/leave/apply')} style={{ background: 'none', border: 'none', color: 'var(--brand-blue)', fontWeight: 600, cursor: 'pointer', marginLeft: '8px' }}>Apply now</button></div>}
                </div>
              )}
            </div>
          </section>

        </div>

        {/* SIDEBAR COLUMN */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          
          {/* Leave Policy Widget */}
          <div className="side-card" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: '24px', color: 'var(--text-muted)' }}>Leave Policy</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--brand-blue)', marginTop: '6px', flexShrink: 0 }}></div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'var(--text-primary)' }}>Annual Leave:</strong> 18 days/year for regular employees
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--brand-red)', marginTop: '6px', flexShrink: 0 }}></div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'var(--text-primary)' }}>Sick Leave:</strong> 12 days/year with medical certificate
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', marginTop: '6px', flexShrink: 0 }}></div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'var(--text-primary)' }}>Casual Leave:</strong> 6 days/year for personal matters
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--draft)', marginTop: '6px', flexShrink: 0 }}></div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'var(--text-primary)' }}>Work from Home:</strong> Available upon manager approval
                </div>
              </div>
            </div>
          </div>

          {/* Tips Widget */}
          <div className="side-card" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: '24px', color: 'var(--text-muted)' }}>Tips</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5, padding: '12px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
                Plan ahead! Submit leave requests at least 3 days in advance for planned leaves.
              </div>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5, padding: '12px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
                For urgent leaves, mark priority as "Urgent" and provide clear reason.
              </div>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5, padding: '12px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
                Always add handover notes to ensure smooth workflow during your absence.
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default LeaveDashboard;
