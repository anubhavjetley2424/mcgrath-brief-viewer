import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  List,
  Mail,
  Activity,
  Map,
} from 'lucide-react';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/deals', label: 'Deals', icon: List },
  { to: '/drafts', label: 'Drafts', icon: Mail },
  { to: '/activities', label: 'Activities', icon: Activity },
  { to: '/map', label: 'Appraisal Map', icon: Map },
];

export default function Sidebar() {
  return (
    <aside
      className="fixed inset-y-0 left-0 z-30 flex flex-col w-[220px]
                 bg-[var(--color-dark-surface-alt)]
                 border-r border-[var(--color-dark-border-subtle)]"
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-[var(--color-dark-border-subtle)]">
        <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] flex items-center justify-center text-white font-bold text-sm">
          MG
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--color-dark-text)] leading-tight">
            McGrath
          </p>
          <p className="text-[11px] text-[var(--color-dark-text-muted)] leading-tight">
            Workflow Hub
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-3 space-y-0.5 overflow-y-auto">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors
              ${
                isActive
                  ? 'bg-[var(--color-dark-primary-light)] text-[var(--color-primary)]'
                  : 'text-[var(--color-dark-text-secondary)] hover:bg-[var(--color-dark-surface-hover)]'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-[var(--color-dark-border-subtle)]">
        <span className="text-[11px] text-[var(--color-dark-text-muted)]">
          Dev Mode
        </span>
      </div>
    </aside>
  );
}
