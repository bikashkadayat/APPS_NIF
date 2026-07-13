import React from 'react';

const Badge = ({ status }) => {
  let className = 'chip ';
  let label = status;

  switch (status.toLowerCase()) {
    case 'draft':
      className += 'ch-draft';
      label = 'Draft';
      break;
    case 'submitted':
    case 'checking':
    case 'review':
      className += 'ch-checking';
      label = 'Checking';
      break;
    case 'approved':
      className += 'ch-approved';
      label = 'Approved';
      break;
    case 'rejected':
      className += 'ch-rejected';
      label = 'Rejected';
      break;
    case 'pending':
      className += 'ch-pending';
      label = 'Pending — Dept Head';
      break;
    case 'pending_hr':
      className += 'ch-checking';
      label = 'Pending — HR';
      break;
    default:
      className += 'ch-pending';
      label = status;
  }

  return <span className={className}>{label}</span>;
};

export default Badge;
