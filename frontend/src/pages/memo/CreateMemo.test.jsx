import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../../services/memoService', () => ({
  memoService: {
    listTemplates: vi.fn(() => Promise.resolve([
      { id: 't1', name: 'General Announcement', memo_type: 'general', subject_template: 'Announcement: Topic', body_template: '<p>Body</p>' },
    ])),
    createMemo: vi.fn(() => Promise.resolve({ id: 'm1', memo_number: 'NIFN-GEN-2026-0001' })),
    createAndSubmit: vi.fn(() => Promise.resolve({ id: 'm1', memo_number: 'NIFN-GEN-2026-0001', status: 'submitted' })),
    submitMemo: vi.fn(() => Promise.resolve({})),
    getAvailableCheckers: vi.fn(() => Promise.resolve([])),
  },
}));
// Keep TipTap + selector out of jsdom; test the form logic.
vi.mock('../../components/memo/RichTextEditor', () => ({ default: ({ value, onChange }) => (
  <textarea aria-label="Body" value={value} onChange={(e) => onChange?.(e.target.value)} />) }));
vi.mock('../../components/memo/UserSelector', () => ({ default: () => <div>checker-selector</div> }));
vi.mock('../../hooks/useAuth', () => ({ useAuth: () => ({ user: { id: 'u1' }, role: 'checker' }) }));

import { memoService } from '../../services/memoService';
import CreateMemo from './CreateMemo';

const renderPage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter><CreateMemo /></MemoryRouter></QueryClientProvider>,
  );
};

describe('CreateMemo', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the form for a non-maker role (checker)', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Create Memo' })).toBeInTheDocument();
    expect(screen.getByLabelText('Title')).toBeInTheDocument();
  });

  it('disables Submit until required fields are filled', () => {
    renderPage();
    const submit = screen.getByRole('button', { name: /Submit for Review/ });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'My memo' } });
    fireEvent.change(screen.getByLabelText('Subject'), { target: { value: 'Subj' } });
    expect(submit).toBeEnabled();
  });

  it('loads a template into the form', async () => {
    renderPage();
    // Wait for the async template option to populate before selecting it.
    await screen.findByRole('option', { name: 'General Announcement' });
    fireEvent.change(screen.getByLabelText('Load template'), { target: { value: 't1' } });
    await waitFor(() => expect(screen.getByLabelText('Subject')).toHaveValue('Announcement: Topic'));
  });

  it('Save as Draft calls createMemo', async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'My memo' } });
    fireEvent.change(screen.getByLabelText('Subject'), { target: { value: 'Subj' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save as Draft' }));
    await waitFor(() => expect(memoService.createMemo).toHaveBeenCalled());
  });
});
