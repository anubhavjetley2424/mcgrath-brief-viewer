import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useNotifications, useUpdateNotification } from '../hooks/useNotifications';
import { timeAgo } from '../lib/utils';

export default function NotificationBell() {
  const { data: notifications = [] } = useNotifications('unread');
  const updateNotif = useUpdateNotification();
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleClick(id: string, actionUrl: string | null) {
    updateNotif.mutate({ id, data: { status: 'read' } });
    setOpen(false);
    if (actionUrl) navigate(actionUrl);
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative flex items-center justify-center w-9 h-9 rounded-lg
                   bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)]
                   hover:bg-[var(--color-surface-active)] dark:hover:bg-[var(--color-dark-surface-active)]
                   text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]
                   transition-colors cursor-pointer"
        aria-label="Notifications"
      >
        <Bell size={18} />
        {notifications.length > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px]
                           px-1 rounded-full bg-[var(--color-danger)] text-white text-[10px] font-bold leading-none">
            {notifications.length > 99 ? '99+' : notifications.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-50 w-80 max-h-96 overflow-y-auto rounded-xl shadow-xl
                        bg-[var(--color-surface-alt)] dark:bg-[var(--color-dark-surface-alt)]
                        border border-[var(--color-border)] dark:border-[var(--color-dark-border)]
                        animate-fade-in">
          <div className="px-4 py-3 border-b border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)]">
            <h3 className="text-xs font-semibold text-[var(--color-text)] dark:text-[var(--color-dark-text)] uppercase tracking-wider">
              Notifications
            </h3>
          </div>

          {notifications.length === 0 ? (
            <div className="px-4 py-6 text-center">
              <p className="text-sm text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)]">
                All caught up!
              </p>
            </div>
          ) : (
            <div>
              {notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleClick(n.id, n.action_url)}
                  className="w-full text-left px-4 py-3 border-b border-[var(--color-border-subtle)] dark:border-[var(--color-dark-border-subtle)] last:border-0
                             hover:bg-[var(--color-surface-hover)] dark:hover:bg-[var(--color-dark-surface-hover)]
                             transition-colors cursor-pointer"
                >
                  <p className="text-sm font-medium text-[var(--color-text)] dark:text-[var(--color-dark-text)] leading-snug">
                    {n.title}
                  </p>
                  {n.body && (
                    <p className="text-xs text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)] mt-0.5 line-clamp-2">
                      {n.body}
                    </p>
                  )}
                  <p className="text-[10px] text-[var(--color-text-muted)] dark:text-[var(--color-dark-text-muted)] mt-1">
                    {timeAgo(n.created_at)}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
