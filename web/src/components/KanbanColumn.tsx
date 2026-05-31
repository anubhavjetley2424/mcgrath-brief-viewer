import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import DealCard from './DealCard';
import type { Deal, Stage } from '../types/api';

const STAGE_COLORS: Record<string, string> = {
  'New Lead': 'bg-blue-500',
  'Listing Appointment Booked': 'bg-indigo-500',
  'Pre-Appointment Prep': 'bg-violet-500',
  'Appraisal Completed': 'bg-amber-500',
  'Negotiation': 'bg-orange-500',
  'Listing Signed': 'bg-rose-500',
  'Campaign Live': 'bg-emerald-500',
  'Sold': 'bg-green-600',
};

interface Props {
  stage: Stage;
  deals: Deal[];
}

export default function KanbanColumn({ stage, deals }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: stage });

  return (
    <div
      ref={setNodeRef}
      className={`kanban-column flex flex-col
        bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
        border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)]
        ${isOver ? 'drag-over' : ''}`}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 mb-3 px-1">
        <div className={`w-2.5 h-2.5 rounded-full ${STAGE_COLORS[stage] || 'bg-gray-400'}`} />
        <h3 className="text-xs font-semibold text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] uppercase tracking-wider truncate">
          {stage}
        </h3>
        <span className="ml-auto text-[11px] font-medium text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)] px-1.5 py-0.5 rounded-md">
          {deals.length}
        </span>
      </div>

      {/* Cards */}
      <SortableContext items={deals.map((d) => d.id)} strategy={verticalListSortingStrategy}>
        <div className="flex-1 space-y-0 min-h-[80px]">
          {deals.map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
        </div>
      </SortableContext>
    </div>
  );
}
