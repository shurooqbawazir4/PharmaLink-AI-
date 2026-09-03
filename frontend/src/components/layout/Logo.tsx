/** PharmaLink AI's connected-care mark, adapted from the supplied brand artwork. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="4.3" fill="currentColor" />
      <path d="M10 12h4M12 10v4" stroke="white" strokeWidth="1.6" />
      <path d="M12 7.7V4.6M15.7 9.9l2.6-1.6M15.7 14.1l2.6 1.6M12 16.3v3.1M8.3 14.1l-2.6 1.6M8.3 9.9 5.7 8.3" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="12" cy="3.4" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="19.4" cy="7.6" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="19.4" cy="16.4" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="12" cy="20.6" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="4.6" cy="16.4" r="1.2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="4.6" cy="7.6" r="1.2" stroke="currentColor" strokeWidth="1.2" />
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
        <LogoMark className="h-6 w-6" />
      </div>
      <span className={wordmarkClassName ?? "text-base font-semibold tracking-tight"}>
        PharmaLink AI
      </span>
    </div>
  );
}
