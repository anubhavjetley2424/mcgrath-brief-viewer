import { Mail, Phone, X, Calendar } from 'lucide-react';
import { useScheduledSends, useCancelScheduledSend } from '../hooks/useScheduledSends';
import { formatDate, timeAgo } from '../lib/utils';

interface Props {
  dealId: string;
}

export default function ScheduledCommsList({ dealId }: Props) {
  const { data: sends = [], isLoading } = useScheduledSends({ deal_id: dealId });
  const cancelSend = useCancelScheduledSend();

  const scheduled = sends.filter((s) => s.status === 'scheduled');
  const past = sends.filter((s) => s.status !== 'scheduled');

  function handleCancel(id: string) {
    if (window.confirm('Cancel this scheduled communication?')) {
      cancelSend.mutate(id);
    }
  }

  if (isLoading) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] py-4 text-center">
        Loading scheduled communications…
      </p>
    );
  }

  if (sends.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
        <Calendar size={32} className="mb-2 opacity-40" />
        <p className="text-sm">No scheduled communications for this deal</p>
      </div>
    );
  }

  return (
    <div>
      {/* Upcoming */}
      {scheduled.length > 0 && (
        <div className="mb-4">
          <h4 className="text-[11px] font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider mb-2 px-1">
            Upcoming ({scheduled.length})
          </h4>
          <div className="rounded-lg border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] overflow-hidden">
            {scheduled.map((s) => (
              <div
                key={s.id}
                className="flex items-start gap-3 py-3 px-3 border-b border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] last:border-0"
              >
                <div className="mt-0.5 p-1.5 rounded-md bg-[var(--color-info-light)] dark:bg-[var(--color-dark-primary-light)]">
                  {s.send_type === 'email' ? (
                    <Mail size={14} className="text-[var(--color-info)]" />
                  ) : (
                    <Phone size={14} className="text-[var(--color-info)]" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--color-text)] dark:text-[var(--color-dark-text)] leading-snug">
                    {s.send_type.toUpperCase()} → {s.recipient}
                  </p>
                  {s.subject && (
                    <p className="text-xs text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] mt-0.5">
                      Subject: {s.subject}
                    </p>
                  )}
                  <p className="text-xs text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] mt-0.5 line-clamp-2">
                    {s.body}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-info-light)] text-[var(--color-info)]">
                      {formatDate(s.scheduled_for)}
                    </span>
                    {s.reason && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
                        {s.reason.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleCancel(s.id)}
                  className="shrink-0 p-1.5 rounded-md hover:bg-[var(--color-danger-light)]
                             text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]
                             hover:text-[var(--color-danger)] transition-colors cursor-pointer"
                  title="Cancel this send"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Past (sent/cancelled/failed) */}
      {past.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider mb-2 px-1">
            History ({past.length})
          </h4>
          <div className="rounded-lg border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] overflow-hidden opacity-60">
            {past.map((s) => (
              <div
                key={s.id}
                className="flex items-start gap-3 py-2.5 px-3 border-b border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] last:border-0"
              >
                <div className="mt-0.5 p-1.5 rounded-md bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)]">
                  {s.send_type === 'email' ? <Mail size={12} /> : <Phone size={12} />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">
                    {s.send_type.toUpperCase()} → {s.recipient}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                        s.status === 'sent'
                          ? 'bg-[var(--color-success-light)] text-[var(--color-success)]'
                          : s.status === 'failed'
                            ? 'bg-[var(--color-danger-light)] text-[var(--color-danger)]'
                            : 'bg-[var(--color-warning-light)] text-[var(--color-warning)]'
                      }`}
                    >
                      {s.status}
                    </span>
                    <span className="text-[10px] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
                      {timeAgo(s.sent_at || s.scheduled_for)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
