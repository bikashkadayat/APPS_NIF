import React from 'react';

// Shown ~30s before an idle auto-logout. Reuses the app's modal styling.
const IdleWarningModal = ({ remaining, onStay, onLogout }) => (
  <div className="modal-overlay" role="alertdialog" aria-modal="true" aria-labelledby="idle-title">
    <div className="modal-content" style={{ maxWidth: 420, textAlign: 'center' }}>
      <h3 id="idle-title" style={{ margin: '0 0 10px', fontSize: 18 }}>Are you still there?</h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: '0 0 8px' }}>
        You will be signed out due to inactivity in
      </p>
      <div style={{ fontSize: 30, fontWeight: 800, color: 'var(--brand-blue)', margin: '0 0 20px' }}>
        {remaining}s
      </div>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button type="button" className="btn btn-ghost" onClick={onLogout}>Log out now</button>
        <button type="button" className="btn btn-primary" onClick={onStay} autoFocus>Stay signed in</button>
      </div>
    </div>
  </div>
);

export default IdleWarningModal;
