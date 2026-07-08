import React from 'react';
import MemoQueue from '../../components/memo/MemoQueue';

const PendingMemoApprovals = () => (
  <MemoQueue mode="approve" title="Pending Approvals" subtitle="Memos awaiting your approval (approver)" />
);

export default PendingMemoApprovals;
