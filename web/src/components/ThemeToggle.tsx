import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export default function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    return document.documentElement.classList.contains('dark');
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  // Initialise from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark') setDark(true);
  }, []);

  return (
    <button
      onClick={() => setDark((d) => !d)}
      className="flex items-center justify-center w-9 h-9 rounded-lg
                 bg-[var(--color-surface-hover)] dark:bg-[var(--color-dark-surface-hover)]
                 hover:bg-[var(--color-surface-active)] dark:hover:bg-[var(--color-dark-surface-active)]
                 text-[var(--color-text-secondary)] dark:text-[var(--color-dark-text-secondary)]
                 transition-colors cursor-pointer"
      aria-label="Toggle dark mode"
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
