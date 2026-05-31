import { useActivities } from '../hooks/useActivities';
import ActivityItem from '../components/ActivityItem';
import { Activity as ActivityIcon } from 'lucide-react';

export default function Activities() {
  const { data: activities = [], isLoading } = useActivities({ limit: 200 });

  return (
    <div className="max-w-3xl animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
          Activity Log
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] mt-1">
          All workflow events across every deal
        </p>
      </div>

      <div className="stat-card">
        {isLoading ? (
          <p className="text-sm text-[var(--color-text-muted)] py-8 text-center">Loading…</p>
        ) : activities.length === 0 ? (
          <div className="text-center py-12">
            <ActivityIcon size={32} className="mx-auto mb-3 text-[var(--color-text-muted)] opacity-40" />
            <p className="text-sm text-[var(--color-text-muted)]">No activities recorded yet</p>
          </div>
        ) : (
          activities.map((a) => <ActivityItem key={a.id} activity={a} />)
        )}
      </div>
    </div>
  );
}
