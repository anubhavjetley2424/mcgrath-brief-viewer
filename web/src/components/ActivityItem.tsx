import { Mail, Phone, Calendar, FileText, AlertCircle } from 'lucide-react';
import type { Activity } from '../types/api';
import { timeAgo } from '../lib/utils';

const CHANNEL_ICON: Record<string, typeof Mail> = {
  email: Mail,
  sms: Phone,
  calendar: Calendar,
  log: FileText,
};

export default function ActivityItem({ activity }: { activity: Activity }) {
  const Icon = CHANNEL_ICON[activity.channels || ''] || AlertCircle;

  return (
    <div className="flex items-start gap-3 py-3 border-b border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] last:border-0 animate-fade-in">
      <div className="mt-0.5 p-1.5 rounded-md bg-[var(--color-primary-light)] dark:bg-[var(--color-dark-primary-light)]">
        <Icon size={14} className="text-[var(--color-primary)]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--color-text)] dark:text-[var(--color-dark-text)] leading-snug">
          {activity.action || 'Activity recorded'}
        </p>
        <div className="flex items-center gap-2 mt-1 text-[11px] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
          {activity.stage && (
            <span className="px-1.5 py-0.5 rounded bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)] font-medium">
              {activity.stage}
            </span>
          )}
          <span>{timeAgo(activity.occurred_at)}</span>
        </div>
      </div>
    </div>
  );
}
