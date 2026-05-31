import { useState, useCallback, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Plus, X } from 'lucide-react';
import StageChangeConfirmModal from '../components/StageChangeConfirmModal';
import { useDeals, useCreateDeal, useUpdateStage } from '../hooks/useDeals';
import { STAGES, type Deal, type DealCreate } from '../types/api';
import { getStageChangePreview } from '../lib/stageChangePreviews';

/* ─── constants ─── */
const SLIDE_PX = 80;
const ROW_H = 52;
const LABEL_W = 200;

const PAL: Record<string, { bar: string; fill: string }> = {
  'New Lead':                   { bar: 'rgba(59,130,246,0.25)',  fill: '#3b82f6' },
  'Listing Appointment Booked': { bar: 'rgba(99,102,241,0.25)',  fill: '#6366f1' },
  'Pre-Appointment Prep':       { bar: 'rgba(139,92,246,0.25)',  fill: '#8b5cf6' },
  'Appraisal Completed':        { bar: 'rgba(245,158,11,0.25)',  fill: '#f59e0b' },
  'Negotiation':                { bar: 'rgba(249,115,22,0.25)',  fill: '#f97316' },
  'Listing Signed':             { bar: 'rgba(244,63,94,0.25)',   fill: '#f43f5e' },
  'Campaign Live':              { bar: 'rgba(16,185,129,0.25)',  fill: '#10b981' },
  'Sold':                       { bar: 'rgba(34,197,94,0.25)',   fill: '#22c55e' },
};

/* ─── helpers ─── */
function nextStage(s: string): string | null {
  const i = STAGES.indexOf(s as (typeof STAGES)[number]);
  return i >= 0 && i < STAGES.length - 1 ? STAGES[i + 1] : null;
}

function pct(d: Date, lo: Date, hi: Date) {
  const t = hi.getTime() - lo.getTime();
  return t <= 0 ? 0 : Math.min(100, Math.max(0, ((d.getTime() - lo.getTime()) / t) * 100));
}

function fmtShort(d: Date) {
  return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short' });
}

/* ═══════════════ GanttRow ═══════════════ */
function GanttRow({ deal, lo, hi, onSlide }: {
  deal: Deal; lo: Date; hi: Date; onSlide: (d: Deal) => void;
}) {
  const [dx, setDx] = useState(0);
  const [on, setOn] = useState(false);
  const refs = useRef({ x0: 0, active: false, dx: 0 });

  const s = deal.stage || 'New Lead';
  const ns = nextStage(s);
  const c = PAL[s] || PAL['New Lead'];
  const l = pct(new Date(deal.created_at), lo, hi);
  const r = pct(new Date(), lo, hi);
  const w = Math.max(r - l, 5);
  const go = dx > SLIDE_PX;

  const down = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!ns) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    refs.current = { x0: e.clientX, active: true, dx: 0 };
    setOn(true);
    setDx(0);
  };
  const move = (e: React.PointerEvent) => {
    if (!refs.current.active) return;
    const d = Math.max(0, e.clientX - refs.current.x0);
    refs.current.dx = d;
    setDx(d);
  };
  const up = () => {
    if (!refs.current.active) return;
    if (refs.current.dx > SLIDE_PX) onSlide(deal);
    refs.current = { x0: 0, active: false, dx: 0 };
    setDx(0);
    setOn(false);
  };

  return (
    <div className="flex items-center border-b border-[var(--color-dark-border-subtle)]/40" style={{ height: ROW_H }}>
      {/* Label */}
      <Link
        to={`/deals/${deal.id}`}
        className="shrink-0 px-4 min-w-0 h-full flex flex-col justify-center
                   border-r border-[var(--color-dark-border-subtle)]/40
                   hover:bg-[var(--color-dark-surface-hover)] transition-colors"
        style={{ width: LABEL_W }}
      >
        <p className="text-[12px] font-medium text-[var(--color-dark-text)] truncate">
          {deal.vendor_name || 'Unnamed'}
        </p>
        {deal.address && (
          <p className="text-[10px] text-[var(--color-dark-text-muted)] truncate">{deal.address}</p>
        )}
      </Link>

      {/* Timeline */}
      <div className="flex-1 relative h-full">
        {/* Bar */}
        <div
          className="absolute rounded-[4px] top-[14px] bottom-[14px]"
          style={{
            left: `${l}%`,
            width: `calc(${w}% + ${on ? dx : 0}px)`,
            background: go
              ? `linear-gradient(90deg, ${c.bar}, rgba(34,197,94,0.35))`
              : c.bar,
            transition: on ? 'none' : 'width 0.3s ease',
          }}
        />
        {/* Handle */}
        <div
          className="absolute top-[12px] bottom-[12px] flex items-center z-10"
          style={{
            left: `calc(${l + w}% + ${on ? dx : 0}px)`,
            transition: on ? 'none' : 'left 0.3s cubic-bezier(0.34,1.56,0.64,1)',
            touchAction: 'none',
            cursor: ns ? 'grab' : 'default',
          }}
          onPointerDown={down}
          onPointerMove={move}
          onPointerUp={up}
          onLostPointerCapture={up}
        >
          <div
            className="px-2 py-0.5 rounded text-[10px] font-bold whitespace-nowrap select-none"
            style={{
              background: go ? '#22c55e' : c.fill,
              color: '#fff',
              boxShadow: on ? `0 0 14px ${c.fill}50` : 'none',
              transition: 'background 0.15s, box-shadow 0.15s',
            }}
          >
            {go && ns ? `→ ${ns}` : s === 'Sold' ? '✓ Sold' : ns ? `${s} →` : '✓ Sold'}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════ Main Page ═══════════════ */
export default function Kanban() {
  const { data: deals = [], isLoading } = useDeals();
  const createDeal = useCreateDeal();
  const updateStage = useUpdateStage();

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<DealCreate>({
    vendor_name: '', vendor_email: '', vendor_phone: '', address: '', stage: 'New Lead',
    bedrooms: undefined, bathrooms: undefined, appraisal_price: undefined,
    access_notes: '', auction_date: '', launch_date: '', settlement_date: '',
  });
  const [pending, setPending] = useState<{ deal: Deal; target: string } | null>(null);

  /* timeline range */
  const { lo, hi, ticks } = useMemo(() => {
    const now = new Date();
    if (!deals.length) {
      const lo = new Date(now); lo.setDate(lo.getDate() - 7);
      const hi = new Date(now); hi.setDate(hi.getDate() + 7);
      return { lo, hi, ticks: [] as Date[] };
    }
    const ts = deals.map(d => new Date(d.created_at).getTime());
    const lo = new Date(Math.min(...ts));
    lo.setHours(0, 0, 0, 0);
    lo.setDate(lo.getDate() - 1);
    const hi = new Date(now);
    hi.setDate(hi.getDate() + 5);
    hi.setHours(23, 59, 59, 999);
    const days = Math.max(14, Math.ceil((hi.getTime() - lo.getTime()) / 86_400_000));
    const step = days <= 14 ? 1 : days <= 30 ? 2 : 7;
    const ticks: Date[] = [];
    const d = new Date(lo);
    while (d <= hi) { ticks.push(new Date(d)); d.setDate(d.getDate() + step); }
    return { lo, hi, ticks };
  }, [deals]);

  /* slide handler */
  function handleSlide(deal: Deal) {
    const ns = nextStage(deal.stage || 'New Lead');
    if (!ns) return;
    const preview = getStageChangePreview(ns);
    if (preview) setPending({ deal, target: ns });
    else updateStage.mutate({ id: deal.id, data: { new_stage: ns, updated_by: 'simon' } });
  }

  const confirmMove = useCallback(() => {
    if (!pending) return;
    updateStage.mutate(
      { id: pending.deal.id, data: { new_stage: pending.target, updated_by: 'simon' } },
      { onSettled: () => setPending(null) },
    );
  }, [pending, updateStage]);

  function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.vendor_name || !form.vendor_email) return;
    // Strip empty strings so backend doesn't try to store '' into numeric/date columns
    const payload: DealCreate = { ...form };
    (Object.keys(payload) as (keyof DealCreate)[]).forEach((k) => {
      const v = payload[k];
      if (v === '' || v === undefined) delete (payload as any)[k];
    });
    createDeal.mutate(payload, {
      onSuccess: () => {
        setShowCreate(false);
        setForm({
          vendor_name: '', vendor_email: '', vendor_phone: '', address: '', stage: 'New Lead',
          bedrooms: undefined, bathrooms: undefined, appraisal_price: undefined,
          access_notes: '', auction_date: '', launch_date: '', settlement_date: '',
        });
      },
    });
  }

  const sorted = [...deals].sort((a, b) => {
    const ai = STAGES.indexOf((a.stage || 'New Lead') as (typeof STAGES)[number]);
    const bi = STAGES.indexOf((b.stage || 'New Lead') as (typeof STAGES)[number]);
    if (ai !== bi) return ai - bi;
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  const now = new Date();

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-dark-text)]">Deals</h1>
          <p className="text-sm text-[var(--color-dark-text-secondary)] mt-1">
            {deals.length} deals · slide handle → to advance stage
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-xs font-semibold
                     bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white transition-colors cursor-pointer"
        >
          <Plus size={16} /> Add Deal
        </button>
      </div>

      {isLoading && <p className="text-sm text-[var(--color-dark-text-muted)]">Loading…</p>}

      {/* Gantt chart */}
      {!isLoading && (
        <div className="rounded-xl border border-[var(--color-dark-border)] bg-[var(--color-dark-surface-alt)] overflow-hidden">
          {/* Date header */}
          <div className="flex" style={{ height: 30 }}>
            <div
              className="shrink-0 border-r border-b border-[var(--color-dark-border)] flex items-end px-4 pb-1"
              style={{ width: LABEL_W }}
            >
              <span className="text-[9px] font-semibold text-[var(--color-dark-text-muted)] uppercase tracking-wider">Deal</span>
            </div>
            <div className="flex-1 relative border-b border-[var(--color-dark-border)]">
              {ticks.map((d, i) => (
                <span
                  key={i}
                  className="absolute text-[9px] font-medium text-[var(--color-dark-text-muted)] -translate-x-1/2 bottom-1"
                  style={{ left: `${pct(d, lo, hi)}%` }}
                >
                  {fmtShort(d)}
                </span>
              ))}
            </div>
          </div>

          {/* Body */}
          <div className="relative"
            style={{
              backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          >
            {/* Grid lines + today marker */}
            <div className="absolute top-0 bottom-0 pointer-events-none" style={{ left: LABEL_W, right: 0 }}>
              {ticks.map((d, i) => (
                <div
                  key={i}
                  className="absolute top-0 bottom-0 w-px"
                  style={{ left: `${pct(d, lo, hi)}%`, background: 'rgba(255,255,255,0.04)' }}
                />
              ))}
              <div
                className="absolute top-0 bottom-0 w-px"
                style={{
                  left: `${pct(now, lo, hi)}%`,
                  background: 'rgba(239,68,68,0.5)',
                  boxShadow: '0 0 8px rgba(239,68,68,0.3)',
                }}
              />
            </div>

            {/* Rows */}
            {sorted.map(deal => (
              <GanttRow key={deal.id} deal={deal} lo={lo} hi={hi} onSlide={handleSlide} />
            ))}
            {sorted.length === 0 && (
              <div className="px-5 py-12 text-center text-sm text-[var(--color-dark-text-muted)]">
                No deals yet. Click "Add Deal" to get started.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stage change confirmation modal */}
      {pending && (() => {
        const preview = getStageChangePreview(pending.target);
        return preview ? (
          <StageChangeConfirmModal
            targetStage={pending.target}
            vendorName={pending.deal.vendor_name || 'Unnamed'}
            previewText={preview}
            isPending={updateStage.isPending}
            onConfirm={confirmMove}
            onCancel={() => setPending(null)}
          />
        ) : null;
      })()}

      {/* Create deal modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <form
            onSubmit={handleCreateSubmit}
            className="w-full max-w-md p-6 rounded-xl bg-[var(--color-dark-surface-alt)]
                       border border-[var(--color-dark-border)] shadow-xl animate-fade-in"
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-[var(--color-dark-text)]">New Deal</h2>
              <button type="button" onClick={() => setShowCreate(false)}
                className="p-1 rounded-md hover:bg-[var(--color-dark-surface-hover)] transition-colors cursor-pointer">
                <X size={18} className="text-[var(--color-dark-text-muted)]" />
              </button>
            </div>
            {/* Contact fields */}
            {[
              { key: 'vendor_name', label: 'Vendor Name *', type: 'text' },
              { key: 'vendor_email', label: 'Vendor Email *', type: 'email' },
              { key: 'vendor_phone', label: 'Phone', type: 'tel' },
              { key: 'address', label: 'Property Address', type: 'text' },
            ].map(({ key, label, type }) => (
              <label key={key} className="block mb-3">
                <span className="text-xs font-medium text-[var(--color-dark-text-secondary)]">{label}</span>
                <input
                  type={type}
                  required={key === 'vendor_name' || key === 'vendor_email'}
                  value={(form as unknown as Record<string, string>)[key] || ''}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-dark-border)]
                             bg-[var(--color-dark-surface)] text-[var(--color-dark-text)]
                             focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                />
              </label>
            ))}

            {/* Property metadata — feeds Airtable form prefill */}
            <div className="mt-4 mb-3 pt-3 border-t border-[var(--color-dark-border-subtle)]/60">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-dark-text-muted)]">
                Property details · pre-fills Simon's forms later
              </p>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-3">
              {[
                { key: 'bedrooms', label: 'Bedrooms', type: 'number' },
                { key: 'bathrooms', label: 'Bathrooms', type: 'number' },
                { key: 'appraisal_price', label: 'Appraisal $', type: 'number' },
              ].map(({ key, label, type }) => (
                <label key={key} className="block">
                  <span className="text-xs font-medium text-[var(--color-dark-text-secondary)]">{label}</span>
                  <input
                    type={type}
                    value={(form as unknown as Record<string, unknown>)[key]?.toString() || ''}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value === '' ? undefined : Number(e.target.value) }))}
                    className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-dark-border)]
                               bg-[var(--color-dark-surface)] text-[var(--color-dark-text)]
                               focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                  />
                </label>
              ))}
            </div>

            <label className="block mb-3">
              <span className="text-xs font-medium text-[var(--color-dark-text-secondary)]">Access Notes</span>
              <input
                type="text"
                placeholder="e.g. lockbox at front · key with neighbour"
                value={form.access_notes || ''}
                onChange={e => setForm(f => ({ ...f, access_notes: e.target.value }))}
                className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-dark-border)]
                           bg-[var(--color-dark-surface)] text-[var(--color-dark-text)]
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
                  <span className="text-xs font-medium text-[var(--color-dark-text-secondary)]">{label}</span>
                  <input
                    type="date"
                    value={(form as unknown as Record<string, string>)[key] || ''}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-dark-border)]
                               bg-[var(--color-dark-surface)] text-[var(--color-dark-text)]
                               focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                  />
                </label>
              ))}
            </div>
            <label className="block mb-5">
              <span className="text-xs font-medium text-[var(--color-dark-text-secondary)]">Initial Stage</span>
              <select
                value={form.stage || 'New Lead'}
                onChange={e => setForm(f => ({ ...f, stage: e.target.value }))}
                className="mt-1 w-full px-3 py-2 rounded-lg text-sm border border-[var(--color-dark-border)]
                           bg-[var(--color-dark-surface)] text-[var(--color-dark-text)]
                           focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              >
                {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowCreate(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--color-dark-surface-hover)]
                           text-[var(--color-dark-text-secondary)] transition-colors cursor-pointer">
                Cancel
              </button>
              <button type="submit" disabled={createDeal.isPending}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--color-primary)]
                           hover:bg-[var(--color-primary-hover)] text-white disabled:opacity-50 transition-colors cursor-pointer">
                {createDeal.isPending ? 'Creating…' : 'Create Deal'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
