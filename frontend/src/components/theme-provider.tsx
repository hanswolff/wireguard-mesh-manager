'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system',
} as const;

type Theme = (typeof THEMES)[keyof typeof THEMES];
type ResolvedTheme = typeof THEMES.LIGHT | typeof THEMES.DARK;

const THEME_STORAGE_KEY = 'theme';
const SYSTEM_THEME_MEDIA_QUERY = '(prefers-color-scheme: dark)';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: ResolvedTheme;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

function getSystemThemeFromMatches(matches: boolean): ResolvedTheme {
  return matches ? THEMES.DARK : THEMES.LIGHT;
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') {
    return THEMES.LIGHT;
  }
  return getSystemThemeFromMatches(
    window.matchMedia(SYSTEM_THEME_MEDIA_QUERY).matches
  );
}

function isValidTheme(theme: string | null): theme is Theme {
  return Object.values(THEMES).includes(theme as Theme);
}

function getStoredTheme(): Theme | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    return isValidTheme(storedTheme) ? storedTheme : null;
  } catch {
    return null;
  }
}

function setStoredTheme(theme: Theme): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Silently fail if localStorage is not available
  }
}

export function ThemeProvider({
  children,
  defaultTheme = THEMES.SYSTEM,
}: {
  children: React.ReactNode;
  defaultTheme?: Theme;
}) {
  const [theme, setTheme] = useState<Theme>(
    () => getStoredTheme() ?? defaultTheme
  );
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(getSystemTheme);

  const resolvedTheme = theme === THEMES.SYSTEM ? systemTheme : theme;

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const root = window.document.documentElement;
    root.classList.remove(THEMES.LIGHT, THEMES.DARK);
    root.classList.add(resolvedTheme);
  }, [resolvedTheme]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(SYSTEM_THEME_MEDIA_QUERY);

    const handleChange = (event?: MediaQueryListEvent) => {
      const nextSystemTheme = getSystemThemeFromMatches(
        event?.matches ?? mediaQuery.matches
      );
      setSystemTheme(nextSystemTheme);
    };

    handleChange();
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const handleSetTheme = useCallback((newTheme: Theme) => {
    setTheme(newTheme);
    setStoredTheme(newTheme);
  }, []);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme: handleSetTheme,
        resolvedTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
