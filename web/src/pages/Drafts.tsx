import { useState } from 'react';
import { Mail, CheckCircle2, XCircle, Edit3 } from 'lucide-react';
import { useDrafts } from '../hooks/useDrafts';
import DraftCard from '../components/DraftCard';

const STATUS_TABS = [
  { key: 'pending_approval', label: 'Pending', icon: Mail },
  { key: 'approved_sent', label: 'Approved', icon: CheckCircle2 },
  { key: 'edited_sent', label: 'Edited & Sent', icon: Edit3 },
  { key: 'discarded', label: 'Discarded', icon: XCircle },
] as const;

export default function Drafts() {
  const [tab, setTab] = useState('pending_approval');
  const { data: drafts = [], isLoading } = useDrafts(tab);

  return (
    <div className="max-w-4xl animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
          Draft Replies
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] mt-1">
          AI-generated replies waiting for your review
        </p>
      </div>

      <div className="flex items-center gap-1 mb-6 p-1 rounded-xl bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)] w-fit">
        {STATUS_TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer
              ${tab === key
                ? 'bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface-alt)] text-[var(--color-text)] dark:text-[var(--color-dark-text)] shadow-sm'
                : 'text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] hover:text-[var(--color-text-secondary)]'}`}
          >
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-sm text-[var(--color-text-muted)] py-8 text-center">Loading…</p>
      ) : drafts.length === 0 ? (
        <div className="stat-card text-center py-12">
          <Mail size={32} className="mx-auto mb-3 text-[var(--color-text-muted)] opacity-40" />
          <p className="text-sm text-[var(--color-text-muted)]">No drafts in this category</p>
        </div>
      ) : (
        <div className="space-y-4">
          {drafts.map((d) => <DraftCard key={d.id} draft={d} />)}
        </div>
      )}
    </div>
  );
}
