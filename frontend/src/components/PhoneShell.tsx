import type { PropsWithChildren } from "react";

type PhoneShellProps = PropsWithChildren<{
  className?: string;
}>;

export function PhoneShell({ children, className }: PhoneShellProps) {
  return (
    <section className={`phone-shell${className ? ` ${className}` : ""}`}>
      <div className="phone-shell__speaker" />
      <div className="phone-shell__screen">{children}</div>
    </section>
  );
}
