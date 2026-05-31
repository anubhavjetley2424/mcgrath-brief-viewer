import { useState } from 'react';
import {
  Check,
  Edit3,
  Trash2,
  AlertTriangle,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { Draft } from '../types/api';
import { intentLabel, timeAgo } from '../lib/utils';
import { useApproveDraft, useEditSendDraft, useDiscardDraft } from '../hooks/useDrafts';

const URGENCY_STYLES: Record<string, string> = {
  high: 'bg-[var(--color-danger-light)] text-[var(--color-danger)] dark:bg-red-950 dark:text-red-400',
  medium: 'bg-[var(--color-warning-light)] text-[var(--color-warning)] dark:bg-amber-950 dark:text-amber-400',
  low: 'bg-[var(--color-success-light)] text-[var(--color-success)] dark:bg-emerald-950 dark:text-emerald-400',
};

interface Props {
  draft: Draft;
}

export default function DraftCard({ draft }: Props) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(draft.suggested_reply || '');
  const [expanded, setExpanded] = useState(false);

  const approve = useApproveDraft();
  const editSend = useEditSendDraft();
  const discard = useDiscardDraft();

  const busy = approve.isPending || editSend.isPending || discard.isPending;
  const email = draft.inbound_emails;

  return (
    <div className="draft-card animate-fade-in">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)] truncate">
            {draft.recipient_email || 'Unknown sender'}
          </p>
          <p className="text-xs text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] truncate mt-0.5">
            {draft.original_subject || 'No subject'}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {draft.urgency && (
            <span
              className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                URGENCY_STYLES[draft.urgency] || ''
              }`}
            >
              {draft.urgency === 'high' && <AlertTriangle size={10} />}
              {draft.urgency}
            </span>
          )}
          {draft.intent && (
            <span className="text-[10px] font-medium text-[var(--color-primary)] bg-[var(--color-primary-light)] dark:bg-[var(--color-dark-primary-light)] px-2 py-0.5 rounded-full">
              {intentLabel(draft.intent)}
            </span>
          )}
        </div>
      </div>

      {/* AI summary */}
      {draft.summary && (
        <div className="flex items-start gap-2 mb-3 p-2.5 rounded-lg bg-[var(--color-primary-surface)] dark:bg-[var(--color-dark-primary-surface)] border border-[var(--color-primary-light)] dark:border-[var(--color-dark-primary-light)]">
          <Sparkles size={14} className="text-[var(--color-primary)] mt-0.5 shrink-0" />
          <p className="text-xs text-[var(--color-text)] dark:text-[var(--color-dark-text)] leading-relaxed">
            {draft.summary}
          </p>
        </div>
      )}

      {/* Original email (expandable) */}
      {email && (
        <div className="mb-3">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="flex items-center gap-1 text-[11px] font-medium text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors cursor-pointer"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            Original email
          </button>
          {expanded && (
            <div className="mt-2 p-3 rounded-lg bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)] border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] text-xs text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] leading-relaxed whitespace-pre-wrap">
              {email.body_preview || 'No body available'}
            </div>
          )}
        </div>
      )}

      {/* Suggested reply / edit area */}
      <div className="mb-4">
        <label className="block text-[11px] font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider mb-1.5">
          {editing ? 'Edit reply' : 'Suggested reply'}
        </label>
        {editing ? (
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={6}
            className="w-full p-3 rounded-lg text-sm border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                       bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface)]
                       text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                       focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-y font-sans leading-relaxed"
          />
        ) : (
          <div className="p-3 rounded-lg bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)] border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] text-xs text-[var(--color-text)] dark:text-[var(--color-dark-text)] leading-relaxed whitespace-pre-wrap max-h-[200px] overflow-y-auto">
            {draft.suggested_reply || 'No suggestion generated'}
          </div>
        )}
      </div>

      {/* Confidence + time */}
      <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] mb-4">
        {draft.confidence != null && (
          <span>Confidence: {(draft.confidence * 100).toFixed(0)}%</span>
        )}
        <span>{timeAgo(draft.created_at)}</span>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        {!editing ? (
          <>
            <button
              disabled={busy}
              onClick={() => approve.mutate(draft.id)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold
                         bg-[var(--color-success)] hover:bg-emerald-600 text-white
                         disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Check size={14} /> Approve & Send
            </button>
            <button
              disabled={busy}
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold
                         bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white
                         disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Edit3 size={14} /> Edit
            </button>
            <button
              disabled={busy}
              onClick={() => discard.mutate(draft.id)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold
                         bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)]
                         text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]
                         hover:bg-[var(--color-danger-light)] hover:text-[var(--color-danger)]
                         disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Trash2 size={14} /> Discard
            </button>
          </>
        ) : (
          <>
            <button
              disabled={busy}
              onClick={() => {
                editSend.mutate({ id: draft.id, data: { edited_reply: editText } });
                setEditing(false);
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold
                         bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white
                         disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Check size={14} /> Send Edited
            </button>
            <button
              disabled={busy}
              onClick={() => {
                setEditText(draft.suggested_reply || '');
                setEditing(false);
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold
                         bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)]
                         text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]
                         disabled:opacity-50 transition-colors cursor-pointer"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}
