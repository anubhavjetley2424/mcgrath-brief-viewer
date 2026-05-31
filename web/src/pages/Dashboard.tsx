import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Columns3,
  Mail,
  TrendingUp,
  Activity as ActivityIcon,
  ClipboardList,
  Square,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { useDeals } from '../hooks/useDeals';
import { useDrafts } from '../hooks/useDrafts';
import { useActivities } from '../hooks/useActivities';
import { useTasks, useUpdateTask } from '../hooks/useTasks';
import ActivityItem from '../components/ActivityItem';
import { STAGES } from '../types/api';

export default function Dashboard() {
  const { data: deals = [] } = useDeals();
  const { data: pendingDrafts = [] } = useDrafts('pending_approval');
  const { data: recentActivities = [] } = useActivities({ limit: 20 });
  const { data: allTasks = [] } = useTasks({ status: 'open' });
  const updateTask = useUpdateTask();

  const stageCounts = STAGES.map((s) => ({
    stage: s,
    count: deals.filter((d) => d.stage === s).length,
  }));

  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const tasksDueToday = useMemo(
    () =>
      allTasks.filter((t) => {
        if (!t.due_date) return false;
        return t.due_date <= todayStr;
      }),
    [allTasks, todayStr],
  );

  return (
    <div className="max-w-6xl animate-fade-in">
      {/* Page title */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
          Dashboard
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] mt-1">
          McGrath Workflow Overview
        </p>
      </div>

      {/* Top stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link to="/deals" className="stat-card group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider">
              Active Deals
            </span>
            <Columns3 size={18} className="text-[var(--color-primary)] opacity-60 group-hover:opacity-100 transition-opacity" />
          </div>
          <p className="text-3xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
            {deals.length}
          </p>
        </Link>

        <Link to="/drafts" className="stat-card group">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider">
              Pending Drafts
            </span>
            <Mail size={18} className="text-[var(--color-warning)] opacity-60 group-hover:opacity-100 transition-opacity" />
          </div>
          <p className="text-3xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
            {pendingDrafts.length}
          </p>
          {pendingDrafts.length > 0 && (
            <span className="inline-flex items-center gap-1 mt-1 text-[10px] font-semibold text-[var(--color-warning)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-warning)] animate-pulse-dot" />
              Needs attention
            </span>
          )}
        </Link>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider">
              Live Listings
            </span>
            <TrendingUp size={18} className="text-[var(--color-success)] opacity-60" />
          </div>
          <p className="text-3xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
            {deals.filter((d) => d.stage === 'Campaign Live').length}
          </p>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider">
              Sold
            </span>
            <ActivityIcon size={18} className="text-[var(--color-success)] opacity-60" />
          </div>
          <p className="text-3xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
            {deals.filter((d) => d.stage === 'Sold').length}
          </p>
        </div>
      </div>

      {/* Pipeline breakdown */}
      <div className="stat-card mb-8">
        <h2 className="text-sm font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)] mb-4">
          Pipeline Breakdown
        </h2>
        <div className="grid grid-cols-8 gap-2">
          {stageCounts.map(({ stage, count }) => (
            <div key={stage} className="text-center">
              <p className="text-2xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
                {count}
              </p>
              <p className="text-[10px] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] leading-tight mt-1">
                {stage}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Tasks Due Today widget */}
      <div className="stat-card mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ClipboardList size={16} className="text-[var(--color-warning)]" />
            <h2 className="text-sm font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
              Tasks Due Today
            </h2>
            {tasksDueToday.length > 0 && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-[var(--color-warning-light)] text-[var(--color-warning)]">
                {tasksDueToday.length}
              </span>
            )}
          </div>
        </div>
        {tasksDueToday.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] py-4 text-center">
            No tasks due today. You're all caught up!
          </p>
        ) : (
          <div className="space-y-0 divide-y divide-[var(--color-border-subtle)] dark:divide-[var(--color-dark-border-subtle)]">
            {tasksDueToday.slice(0, 8).map((task) => {
              const isOverdue = task.due_date! < todayStr;
              const deal = deals.find((d) => d.id === task.deal_id);
              return (
                <div key={task.id} className="flex items-center gap-3 py-2.5">
                  <button
                    onClick={() => updateTask.mutate({ id: task.id, data: { status: 'done' } })}
                    className="shrink-0 text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]
                               hover:text-[var(--color-success)] transition-colors cursor-pointer"
                  >
                    <Square size={16} />
                  </button>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--color-text)] dark:text-[var(--color-dark-text)] truncate">
                      {task.title}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {deal && (
                        <Link
                          to={`/deals/${deal.id}`}
                          className="text-[10px] font-medium text-[var(--color-primary)] hover:underline truncate"
                        >
                          {deal.vendor_name || deal.address || 'Deal'}
                        </Link>
                      )}
                      {isOverdue && (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-danger-light)] text-[var(--color-danger)]">
                          <Clock size={9} /> overdue
                        </span>
                      )}
                    </div>
                  </div>
                  {task.external_url && (
                    <a
                      href={task.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 text-[var(--color-primary)]"
                    >
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent activity feed */}
      <div className="stat-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
            Recent Activity
          </h2>
          <Link
            to="/activities"
            className="text-xs font-medium text-[var(--color-primary)] hover:underline"
          >
            View all →
          </Link>
        </div>
        {recentActivities.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] py-6 text-center">
            No activities yet. Trigger a workflow to see events here.
          </p>
        ) : (
          <div>
            {recentActivities.slice(0, 10).map((a) => (
              <ActivityItem key={a.id} activity={a} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
