import React, { useEffect } from 'react';
import DOMPurify from 'dompurify';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import { Bold, Italic, Heading2, Heading3, List, ListOrdered, Link as LinkIcon } from 'lucide-react';

// Read-path sanitization (defense in depth; the backend also sanitizes on
// write). Allowlist mirrors what the editor toolbar can produce.
const PURIFY_CONFIG = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h2', 'h3', 'ul', 'ol', 'li', 'a', 'blockquote'],
  ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
};
const sanitize = (html) => DOMPurify.sanitize(html || '', PURIFY_CONFIG);

/**
 * TipTap rich-text editor. Emits an HTML string via onChange (stored for future
 * PDF rendering). readOnly renders the stored HTML. Falls back to a <textarea>
 * if the editor fails to initialize.
 *
 * @param {{value?:string, onChange?:(html:string)=>void, placeholder?:string,
 *          readOnly?:boolean, minHeight?:number}} props
 */
const RichTextEditor = ({ value = '', onChange, placeholder = 'Write the memo body…', readOnly = false, minHeight = 180 }) => {
  const editor = useEditor({
    extensions: [StarterKit, Link.configure({ openOnClick: false, autolink: true })],
    content: value || '',
    editable: !readOnly,
    immediatelyRender: false,
    onUpdate: ({ editor: ed }) => onChange?.(ed.getHTML()),
  });

  // Sync external value changes (e.g. loading a template) without cursor jumps.
  useEffect(() => {
    if (editor && !readOnly && value !== editor.getHTML()) {
      editor.commands.setContent(value || '', false);
    }
  }, [value, editor, readOnly]);

  if (readOnly) {
    return <div className="lr-richtext-view" dangerouslySetInnerHTML={{ __html: sanitize(value) || '<p><em>No content.</em></p>' }} />;
  }

  if (!editor) {
    return (
      <textarea
        className="lr-field" style={{ minHeight, width: '100%' }}
        defaultValue={value} placeholder={placeholder}
        onChange={(e) => onChange?.(e.target.value)}
        aria-label="Memo body"
      />
    );
  }

  const btn = (active, onClick, title, children) => (
    <button type="button" title={title} aria-label={title} aria-pressed={active}
      className={`lr-rt-btn ${active ? 'on' : ''}`} onClick={onClick}>{children}</button>
  );
  const setLink = () => {
    const url = window.prompt('Link URL:');
    if (url === null) return;
    if (url === '') editor.chain().focus().unsetLink().run();
    else editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  };

  return (
    <div className="lr-richtext">
      <div className="lr-rt-toolbar" role="toolbar" aria-label="Formatting">
        {btn(editor.isActive('bold'), () => editor.chain().focus().toggleBold().run(), 'Bold', <Bold size={15} />)}
        {btn(editor.isActive('italic'), () => editor.chain().focus().toggleItalic().run(), 'Italic', <Italic size={15} />)}
        {btn(editor.isActive('heading', { level: 2 }), () => editor.chain().focus().toggleHeading({ level: 2 }).run(), 'Heading 2', <Heading2 size={15} />)}
        {btn(editor.isActive('heading', { level: 3 }), () => editor.chain().focus().toggleHeading({ level: 3 }).run(), 'Heading 3', <Heading3 size={15} />)}
        {btn(editor.isActive('bulletList'), () => editor.chain().focus().toggleBulletList().run(), 'Bullet list', <List size={15} />)}
        {btn(editor.isActive('orderedList'), () => editor.chain().focus().toggleOrderedList().run(), 'Numbered list', <ListOrdered size={15} />)}
        {btn(editor.isActive('blockquote'), () => editor.chain().focus().toggleBlockquote().run(), 'Quote', '❝')}
        {btn(editor.isActive('link'), setLink, 'Link', <LinkIcon size={15} />)}
      </div>
      <EditorContent editor={editor} className="lr-rt-content" style={{ minHeight }} />
    </div>
  );
};

export default RichTextEditor;
