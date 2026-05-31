import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Mail, Phone, Calendar, ClipboardList, Send, Activity as ActivityIcon, Pencil, X, Home } from 'lucide-react';
import { useDeal, useUpdateStage, useUpdateDeal } from '../hooks/useDeals';
import ActivityItem from '../components/ActivityItem';
import TasksList from '../components/TasksList';
import ScheduledCommsList from '../components/ScheduledCommsList';
import { STAGES, type DealUpdate } from '../types/api';
import { formatDate } from '../lib/utils';

type Tab = 'activity' | 'tasks' | 'scheduled';

export default function DealDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: deal, isLoading, error } = useDeal(id || '');
  const updateStage = useUpdateStage();
  const updateDeal = useUpdateDeal();
  const [tab, setTab] = useState<Tab>('tasks');
  const [editOpen, setEditOpen] = useState(false);
  const [edit, setEdit] = useState<DealUpdate>({});

  /* Seed the edit form whenever the deal loads or modal opens */
  useEffect(() => {
    if (deal && editOpen) {
      setEdit({
        vendor_name: deal.vendor_name ?? '',
        vendor_email: deal.vendor_email ?? '',
        vendor_phone: deal.vendor_phone ?? '',
        address: deal.address ?? '',
        bedrooms: deal.bedrooms ?? undefined,
        bathrooms: deal.bathrooms ?? undefined,
        appraisal_price: deal.appraisal_price ?? undefined,
        access_notes: deal.access_notes ?? '',
        auction_date: deal.auction_date ?? '',
        launch_date: deal.launch_date ?? '',
        settlement_date: deal.settlement_date ?? '',
        notes: deal.notes ?? '',
      });
    }
  }, [deal, editOpen]);

  function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!deal) return;
    const payload: DealUpdate = { ...edit, updated_by: 'simon' };
    // Strip empty strings → backend stores null instead of '' for numeric/date cols
    (Object.keys(payload) as (keyof DealUpdate)[]).forEach((k) => {
      if (payload[k] === '' || payload[k] === undefined) {
        delete (payload as Record<string, unknown>)[k];
      }
    });
    updateDeal.mutate({ id: deal.id, data: payload }, {
      onSuccess: () => setEditOpen(false),
    });
  }

  if (isLoading) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] py-12">
        Loading deal…
      </p>
    );
  }
  if (error || !deal) {
    return (
      <p className="text-sm text-[var(--color-danger)] py-12">
        Deal not found.
      </p>
    );
  }

  const tabs: { key: Tab; label: string; icon: typeof ClipboardList }[] = [
    { key: 'tasks', label: 'Tasks', icon: ClipboardList },
    { key: 'scheduled', label: 'Scheduled Comms', icon: Send },
    { key: 'activity', label: 'Activity', icon: ActivityIcon },
  ];

  return (
    <div className="max-w-3xl animate-fade-in">
      {/* Back link */}
      <Link
        to="/deals"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] hover:text-[var(--color-primary)] transition-colors mb-6"
      >
        <ArrowLeft size={14} /> Back to Kanban
      </Link>

      {/* Header */}
      <div className="stat-card mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
              {deal.vendor_name || 'Unnamed Deal'}
            </h1>
            <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">
              {deal.address && (
                <span className="flex items-center gap-1.5"><MapPin size={14} /> {deal.address}</span>
              )}
              {deal.vendor_email && (
                <span className="flex items-center gap-1.5"><Mail size={14} /> {deal.vendor_email}</span>
              )}
              {deal.vendor_phone && (
                <span className="flex items-center gap-1.5"><Phone size={14} /> {deal.vendor_phone}</span>
              )}
            </div>

            {/* Property facts */}
            {(deal.bedrooms || deal.bathrooms || deal.appraisal_price) && (
              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
                <Home size={12} className="inline" />
                {deal.bedrooms != null && <span>{deal.bedrooms} bed</span>}
                {deal.bathrooms != null && <span>{deal.bathrooms} bath</span>}
                {deal.appraisal_price != null && (
                  <span>${Number(deal.appraisal_price).toLocaleString('en-AU')}</span>
                )}
                {deal.auction_date && <span>· Auction {deal.auction_date}</span>}
                {deal.launch_date && <span>· Launch {deal.launch_date}</span>}
                {deal.settlement_date && <span>· Settlement {deal.settlement_date}</span>}
              </div>
            )}

            <p className="text-xs text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] mt-2">
              <Calendar size={11} className="inline mr-1" />
              Created {formatDate(deal.created_at)}
              {deal.updated_at && <> · Updated {formatDate(deal.updated_at)}</>}
              {deal.updated_by && <> by {deal.updated_by}</>}
            </p>
          </div>

          {/* Edit button */}
          <button
            onClick={() => setEditOpen(true)}
            className="shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold
                       bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface-alt)]
                       hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)]
                       text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]
                       border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                       transition-colors cursor-pointer"
          >
            <Pencil size={12} /> Edit Details
          </button>
        </div>

        {/* Stage selector */}
        <div className="mt-5 pt-4 border-t border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)]">
          <label className="text-[11px] font-semibold text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] uppercase tracking-wider">
            Current Stage
          </label>
          <select
            value={deal.stage || 'New Lead'}
            onChange={(e) =>
              updateStage.mutate({
                id: deal.id,
                data: { new_stage: e.target.value, updated_by: 'simon' },
              })
            }
            className="mt-1.5 block w-full max-w-xs px-3 py-2 rounded-lg text-sm border
                       border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                       bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                       text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                       focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            {STAGES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Notes */}
      {deal.notes && (
        <div className="stat-card mb-6">
          <h2 className="text-sm font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)] mb-2">
            Notes
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] whitespace-pre-wrap">
            {deal.notes}
          </p>
        </div>
      )}

      {/* Tab navigation */}
      <div className="flex gap-1 mb-4 p-1 rounded-lg bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                      border border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)]">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-xs font-semibold transition-colors cursor-pointer
              ${tab === key
                ? 'bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface-alt)] text-[var(--color-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] hover:text-[var(--color-text-secondary)] dark:hover:text-[var(--color-dark-text-secondary)]'
              }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="stat-card">
        {tab === 'tasks' && <TasksList dealId={deal.id} />}

        {tab === 'scheduled' && <ScheduledCommsList dealId={deal.id} />}

        {tab === 'activity' && (
          <>
            <h2 className="text-sm font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)] mb-4">
              Activity Timeline
            </h2>
            {deal.activities && deal.activities.length > 0 ? (
              deal.activities.map((a) => <ActivityItem key={a.id} activity={a} />)
            ) : (
              <p className="text-sm text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] py-4 text-center">
                No activities recorded for this deal yet.
              </p>
            )}
          </>
        )}
      </div>

      {/* Edit Property Details modal */}
      {editOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <form
            onSubmit={handleEditSubmit}
            className="w-full max-w-lg p-6 rounded-xl bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface-alt)]
                       border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                       shadow-xl animate-fade-in max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-[var(--color-text)] dark:text-[var(--color-dark-text)]">
                Edit Property Details
              </h2>
              <button
                type="button"
                onClick={() => setEditOpen(false)}
                className="p-1 rounded-md hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)] transition-colors cursor-pointer"
              >
                <X size={18} className="text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]" />
              </button>
            </div>

            {/* Contact + address */}
            {[
              { key: 'vendor_name', label: 'Vendor Name', type: 'text' },
              { key: 'vendor_email', label: 'Vendor Email', type: 'email' },
              { key: 'vendor_phone', label: 'Phone', type: 'tel' },
              { key: 'address', label: 'Property Address', type: 'text' },
            ].map(({ key, label, type }) => (
              <label key={key} className="block mb-3">
                <span className="text-xs font-medium text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">{label}</span>
                <input
                  type={type}
                  value={(edit as Record<string, unknown>)[key]?.toString() || ''}
                  onChange={(e) => setEdit((f) => ({ ...f, [key]: e.target.value }))}
                  className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                             bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                             text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                             focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                />
              </label>
            ))}

            {/* Property facts */}
            <div className="mt-4 mb-3 pt-3 border-t border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)]/60">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
                Pre-fill values for Simon's 8 Airtable forms
              </p>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-3">
              {[
                { key: 'bedrooms', label: 'Bedrooms' },
                { key: 'bathrooms', label: 'Bathrooms' },
                { key: 'appraisal_price', label: 'Appraisal $' },
              ].map(({ key, label }) => (
                <label key={key} className="block">
                  <span className="text-xs font-medium text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">{label}</span>
                  <input
                    type="number"
                    value={(edit as Record<string, unknown>)[key]?.toString() || ''}
                    onChange={(e) =>
                      setEdit((f) => ({ ...f, [key]: e.target.value === '' ? undefined : Number(e.target.value) }))
                    }
                    className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                               bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                               text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                               focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                  />
                </label>
              ))}
            </div>

            <label className="block mb-3">
              <span className="text-xs font-medium text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">Access Notes</span>
              <input
                type="text"
                placeholder="e.g. lockbox at front · key with neighbour"
                value={edit.access_notes || ''}
                onChange={(e) => setEdit((f) => ({ ...f, access_notes: e.target.value }))}
                className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                           bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                           text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                           focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
            </label>

            <div className="grid grid-cols-3 gap-2 mb-4">
              {[
                { key: 'auction_date', label: 'Auction Date' },
                { key: 'launch_date', label: 'Launch Date' },
                { key: 'settlement_date', label: 'Settlement Date' },
              ].map(({ key, label }) => (
                <label key={key} className="block">
                  <span className="text-xs font-medium text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">{label}</span>
                  <input
                    type="date"
                    value={(edit as Record<string, string>)[key] || ''}
                    onChange={(e) => setEdit((f) => ({ ...f, [key]: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                               bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                               text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                               focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                  />
                </label>
              ))}
            </div>

            {/* Notes */}
            <label className="block mb-5">
              <span className="text-xs font-medium text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]">Notes</span>
              <textarea
                rows={3}
                value={edit.notes || ''}
                onChange={(e) => setEdit((f) => ({ ...f, notes: e.target.value }))}
                className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                           bg-[var(--color-surface)] dark:bg-[var(--color-dark-surface)]
                           text-[var(--color-text)] dark:text-[var(--color-dark-text)]
                           focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
            </label>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditOpen(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)]
                           text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]
                           transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={updateDeal.isPending}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--color-primary)]
                           hover:bg-[var(--color-primary-hover)] text-white disabled:opacity-50 transition-colors cursor-pointer"
              >
                {updateDeal.isPending ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
