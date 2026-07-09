import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../../services/memoService', () => ({
  memoService: {
    // Server search-gates + de-PIIs the directory (H5): no email/role fields.
    getAvailableCheckers: vi.fn((q) => Promise.resolve(
      (q || '').toLowerCase().includes('other')
        ? [{ id: 'c2', full_name: 'Other Checker', department: 'HR' }]
        : [{ id: 'c1', full_name: 'Chandra Checker', department: 'ENG' }],
    )),
    getAvailableApprovers: vi.fn(() => Promise.resolve([])),
  },
}));

import UserSelector from './UserSelector';

const wrap = (ui) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
};

describe('UserSelector', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows the Auto-assign option when allowAuto', async () => {
    wrap(<UserSelector role="checker" value="" onChange={() => {}} allowAuto />);
    fireEvent.click(screen.getByRole('button', { name: /Auto-assign|Select/ }));
    // The trigger label and the menu option both read "Auto-assign…"; assert the option.
    expect(await screen.findByRole('option', { name: /Auto-assign by department/ })).toBeInTheDocument();
  });

  it('requires >= 2 characters before searching (no enumeration)', async () => {
    wrap(<UserSelector role="checker" value="" onChange={() => {}} allowAuto />);
    fireEvent.click(screen.getByRole('button'));
    // Nothing loaded until the user types the minimum query length.
    expect(screen.getByText(/Type at least 2 characters/i)).toBeInTheDocument();
    expect(screen.queryByText('Chandra Checker')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Search checkers'), { target: { value: 'ch' } });
    expect(await screen.findByText('Chandra Checker')).toBeInTheDocument();
  });

  it('searches server-side and never shows an email', async () => {
    wrap(<UserSelector role="checker" value="" onChange={() => {}} allowAuto />);
    fireEvent.click(screen.getByRole('button'));
    fireEvent.change(screen.getByLabelText('Search checkers'), { target: { value: 'other' } });
    await screen.findByText('Other Checker');
    expect(screen.queryByText(/@/)).not.toBeInTheDocument();
  });

  it('calls onChange with the picked user id', async () => {
    const onChange = vi.fn();
    wrap(<UserSelector role="checker" value="" onChange={onChange} allowAuto />);
    fireEvent.click(screen.getByRole('button'));
    fireEvent.change(screen.getByLabelText('Search checkers'), { target: { value: 'ch' } });
    fireEvent.click(await screen.findByText('Chandra Checker'));
    expect(onChange).toHaveBeenCalledWith('c1');
  });
});
