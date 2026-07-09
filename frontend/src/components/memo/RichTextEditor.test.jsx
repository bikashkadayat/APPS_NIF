import React from 'react';
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import RichTextEditor from './RichTextEditor';

// C1 (read-path, defense in depth): the readOnly renderer must sanitize the
// stored HTML with DOMPurify before injecting it via dangerouslySetInnerHTML.
describe('RichTextEditor sanitization', () => {
  it('strips script/img/onerror from rendered body', () => {
    const { container } = render(
      <RichTextEditor readOnly value={'<p>ok</p><script>alert(1)</script><img src=x onerror="alert(2)">'} />,
    );
    const html = container.innerHTML;
    expect(html).toContain('<p>ok</p>');
    expect(html.toLowerCase()).not.toContain('<script');
    expect(html.toLowerCase()).not.toContain('<img');
    expect(html.toLowerCase()).not.toContain('onerror');
    expect(container.querySelector('img')).toBeNull();
  });

  it('preserves allowed formatting', () => {
    const { container } = render(
      <RichTextEditor readOnly value={'<p><strong>b</strong></p><ul><li>x</li></ul>'} />,
    );
    expect(container.querySelector('strong')).not.toBeNull();
    expect(container.querySelector('li')).not.toBeNull();
  });
});
