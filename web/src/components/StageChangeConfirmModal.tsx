import { AlertTriangle, X } from 'lucide-react';

interface Props {
  targetStage: string;
  vendorName: string;
  previewText: string;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function StageChangeConfirmModal({
  targetStage,
  vendorName,
  previewText,
  isPending,
  onConfirm,
  onCancel,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md p-6 rounded-xl
                      bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface-alt)]
                      border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                      shadow-xl animate-fade-in">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-warning-light)]">
              <AlertTriangle size={20} className="text-[var(--color-warning)]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
                Move to {targetStage}?
              </h2>
              <p className="text-xs text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] mt-0.5">
                {vendorName}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 rounded-md hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)] transition-colors cursor-pointer"
          >
            <X size={18} className="text-[var(--color-text-muted)]" />
          </button>
        </div>

        {/* Preview text */}
        <div className="mb-5 p-3 rounded-lg bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                        border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)]">
          <p className="text-sm text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] leading-relaxed">
            {previewText}
          </p>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-4 py-2 rounded-lg text-xs font-semibold
                       bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)]
                       text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]
                       transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="px-4 py-2 rounded-lg text-xs font-semibold
                       bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white
                       disabled:opacity-50 transition-colors cursor-pointer"
          >
            {isPending ? 'Moving…' : 'Confirm & Move'}
          </button>
        </div>
      </div>
    </div>
  );
}
