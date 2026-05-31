import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import NotificationBell from './NotificationBell';

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-[220px] flex flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex items-center justify-end gap-3 px-6 lg:px-8 py-3
                           bg-[var(--color-dark-surface)]/80
                           backdrop-blur-md border-b border-[var(--color-dark-border-subtle)]">
          <NotificationBell />
        </header>
        <main className="flex-1 p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
