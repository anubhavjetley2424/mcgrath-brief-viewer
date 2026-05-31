import { useState } from 'react';
import {
  CheckSquare,
  Square,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  Clock,
} from 'lucide-react';
import type { Task, TaskStatus } from '../types/api';
import { formatDate } from '../lib/utils';

interface Props {
  task: Task;
  onStatusChange: (id: string, status: TaskStatus) => void;
}

export default function TaskRow({ task, onStatusChange }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const isDone = task.status === 'done';
  const isSkipped = task.status === 'skipped';
  const isOverdue =
    task.due_date && !isDone && !isSkipped && new Date(task.due_date) < new Date();

  function handleToggle() {
    onStatusChange(task.id, isDone ? 'open' : 'done');
  }

  return (
    <div
      className={`group border-b border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] last:border-0
        ${isDone || isSkipped ? 'opacity-60' : ''}`}
    >
      <div className="flex items-start gap-3 py-3 px-1">
        {/* Checkbox */}
        <button
          onClick={handleToggle}
          className="mt-0.5 shrink-0 text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]
                     hover:text-[var(--color-primary)] transition-colors cursor-pointer"
        >
          {isDone ? (
            <CheckSquare size={18} className="text-[var(--color-success)]" />
          ) : (
            <Square size={18} />
          )}
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {task.description && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="shrink-0 text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] cursor-pointer"
              >
                {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
            )}
            <p
              className={`text-sm leading-snug ${
                isDone
                  ? 'line-through text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]'
                  : 'text-[var(--color-text)] dark:text-[var(--color-dark-text)]'
              }`}
            >
              {task.title}
            </p>
          </div>

          {/* Expanded description */}
          {expanded && task.description && (
            <p className="mt-1.5 ml-5 text-xs text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] whitespace-pre-wrap">
              {task.description}
            </p>
          )}

          {/* Meta row */}
          <div className="flex items-center gap-2 mt-1.5 ml-5">
            {task.due_date && (
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded
                  ${
                    isOverdue
                      ? 'bg-[var(--color-danger-light)] text-[var(--color-danger)]'
                      : 'bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]'
                  }`}
              >
                <Clock size={10} />
                {formatDate(task.due_date)}
              </span>
            )}
            {task.task_type && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-primary-light)] dark:bg-[var(--color-dark-primary-light)] text-[var(--color-primary)]">
                {task.task_type.replace('_', ' ')}
              </span>
            )}
            {isSkipped && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--color-warning-light)] text-[var(--color-warning)]">
                skipped
              </span>
            )}
          </div>
        </div>

        {/* External link */}
        {task.external_url && (
          <a
            href={task.external_url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 p-1.5 rounded-md hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)]
                       text-[var(--color-primary)] transition-colors"
            title="Open external link"
          >
            <ExternalLink size={14} />
          </a>
        )}

        {/* Context menu */}
        <div className="relative shrink-0">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-1.5 rounded-md opacity-0 group-hover:opacity-100
                       hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)]
                       text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]
                       transition-all cursor-pointer"
          >
            <MoreHorizontal size={14} />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-8 z-50 w-40 py-1 rounded-lg shadow-lg
                              bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface-alt)]
                              border border-[var(--color-border)] dark:border-[var(--color-dark-border)]">
                {!isDone && (
                  <button
                    onClick={() => { onStatusChange(task.id, 'in_progress'); setMenuOpen(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                               hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)] cursor-pointer"
                  >
                    Mark In Progress
                  </button>
                )}
                {!isSkipped && (
                  <button
                    onClick={() => { onStatusChange(task.id, 'skipped'); setMenuOpen(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                               hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)] cursor-pointer"
                  >
                    Skip
                  </button>
                )}
                {(isDone || isSkipped) && (
                  <button
                    onClick={() => { onStatusChange(task.id, 'open'); setMenuOpen(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                               hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)] cursor-pointer"
                  >
                    Re-open
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
