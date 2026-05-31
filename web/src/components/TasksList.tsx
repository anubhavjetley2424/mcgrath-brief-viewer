import { useMemo } from 'react';
import { ClipboardList } from 'lucide-react';
import TaskRow from './TaskRow';
import { useTasks, useUpdateTask } from '../hooks/useTasks';
import { STAGES, type TaskStatus } from '../types/api';

interface Props {
  dealId: string;
  stageFilter?: string;
}

export default function TasksList({ dealId, stageFilter }: Props) {
  const { data: allTasks = [], isLoading } = useTasks({ deal_id: dealId });
  const updateTask = useUpdateTask();

  const tasks = useMemo(() => {
    if (!stageFilter) return allTasks;
    return allTasks.filter((t) => t.stage === stageFilter);
  }, [allTasks, stageFilter]);

  const grouped = useMemo(() => {
    const map: Record<string, typeof tasks> = {};
    tasks.forEach((t) => {
      const stage = t.stage || 'Uncategorised';
      if (!map[stage]) map[stage] = [];
      map[stage].push(t);
    });
    return map;
  }, [tasks]);

  const stageOrder = useMemo(() => {
    const stageSet = new Set(Object.keys(grouped));
    const ordered = STAGES.filter((s) => stageSet.has(s));
    const remaining = [...stageSet].filter((s) => !(STAGES as readonly string[]).includes(s));
    return [...ordered, ...remaining];
  }, [grouped]);

  function handleStatusChange(id: string, status: TaskStatus) {
    updateTask.mutate({ id, data: { status } });
  }

  const totalTasks = tasks.length;
  const doneTasks = tasks.filter((t) => t.status === 'done').length;

  if (isLoading) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] py-4 text-center">
        Loading tasks…
      </p>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
        <ClipboardList size={32} className="mb-2 opacity-40" />
        <p className="text-sm">No tasks for this {stageFilter ? 'stage' : 'deal'} yet</p>
      </div>
    );
  }

  return (
    <div>
      {/* Overall progress */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-semibold text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">
          {doneTasks} of {totalTasks} tasks complete
        </p>
        <div className="w-24 h-1.5 rounded-full bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)] overflow-hidden">
          <div
            className="h-full rounded-full bg-[var(--color-success)] transition-all"
            style={{ width: `${totalTasks > 0 ? (doneTasks / totalTasks) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Grouped by stage */}
      {stageOrder.map((stage) => {
        const stageTasks = grouped[stage];
        const stageComplete = stageTasks.filter((t) => t.status === 'done').length;
        const stageTotal = stageTasks.length;
        const pct = stageTotal > 0 ? Math.round((stageComplete / stageTotal) * 100) : 0;

        return (
          <div key={stage} className="mb-4 last:mb-0">
            {!stageFilter && stageOrder.length > 1 && (
              <div className="flex items-center justify-between mb-1 px-1">
                <h4 className="text-[11px] font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider">
                  {stage}
                </h4>
                <span className="text-[10px] font-medium text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
                  {pct}%
                </span>
              </div>
            )}
            <div className="rounded-lg border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] overflow-hidden">
              {stageTasks.map((task) => (
                <TaskRow key={task.id} task={task} onStatusChange={handleStatusChange} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
