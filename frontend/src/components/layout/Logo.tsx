/** MedCycle AI's mark: a redistribution/cycle arrow around a medical
 * cross — "cycle" (moving stock between hospitals, closing the loop on
 * waste) + "med" in one glyph, rather than a generic pulse/heartbeat icon.
 * `currentColor` throughout so it inherits text color from its container
 * (the brand-blue badge in Sidebar/AuthLayout, or plain text on the
 * landing page's dark hero). */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M20.5 3.5v5h-5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M9 12h6M12 9v6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({
  className,
  wordmarkClassName,
}: {
  className?: string;
  wordmarkClassName?: string;
}) {
  return (
    <div className={className ?? "flex items-center gap-2"}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <LogoMark className="h-4.5 w-4.5" />
      </div>
      <span className={wordmarkClassName ?? "text-base font-semibold tracking-tight"}>
        MedCycle AI
      </span>
    </div>
  );
}
