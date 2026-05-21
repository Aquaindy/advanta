import { useThemeStore } from "@/stores/theme-store";
import { cn } from "@/lib/utils";

/**
 * Light/dark toggle. Defaults to following the OS until the user clicks, then
 * the explicit choice is persisted. Shows a sun in dark mode (→ switch to
 * light) and a moon in light mode (→ switch to dark).
 *
 * `tone="brand"` is for placement on a grape/dark surface (e.g. the sidebar),
 * where the control should read as light-on-color in both themes.
 */
export function ThemeToggle({
  className,
  tone = "default",
}: {
  className?: string;
  tone?: "default" | "brand";
}) {
  const resolved = useThemeStore((s) => s.resolved);
  const toggle = useThemeStore((s) => s.toggle);
  const isDark = resolved === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className={cn(
        "inline-flex size-9 items-center justify-center rounded-xl border transition",
        tone === "brand"
          ? "border-white/20 text-white hover:bg-white/10"
          : "border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-ink",
        className,
      )}
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

function SunIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32 1.41-1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}
