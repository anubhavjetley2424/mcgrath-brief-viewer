import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Link } from 'react-router-dom';
import { MapPin, User } from 'lucide-react';
import type { Deal } from '../types/api';
import { timeAgo } from '../lib/utils';

interface Props {
  deal: Deal;
}

export default function DealCard({ deal }: Props) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: deal.id, data: { deal } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`deal-card mb-2.5 animate-fade-in ${isDragging ? 'dragging' : ''}`}
    >
      <Link
        to={`/deals/${deal.id}`}
        className="block"
        onClick={(e) => {
          // Prevent navigation when dragging
          if (isDragging) e.preventDefault();
        }}
      >
        <div className="flex items-start justify-between gap-2 mb-1.5">
          <p className="text-sm font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)] leading-snug truncate">
            {deal.vendor_name || 'Unnamed'}
          </p>
        </div>
        {deal.address && (
          <div className="flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] mb-1">
            <MapPin size={12} className="shrink-0" />
            <span className="truncate">{deal.address}</span>
          </div>
        )}
        {deal.vendor_email && (
          <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
            <User size={11} className="shrink-0" />
            <span className="truncate">{deal.vendor_email}</span>
          </div>
        )}
        <p className="text-[10px] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] mt-2">
          {timeAgo(deal.updated_at || deal.created_at)}
        </p>
      </Link>
    </div>
  );
}
