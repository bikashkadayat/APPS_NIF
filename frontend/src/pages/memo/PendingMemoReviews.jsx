import React from 'react';
import MemoQueue from '../../components/memo/MemoQueue';

const PendingMemoReviews = () => (
  <MemoQueue mode="review" title="Pending Reviews" subtitle="Memos awaiting your review (checker)" />
);

export default PendingMemoReviews;
