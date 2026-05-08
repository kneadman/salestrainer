import type { HTMLAttributes, ReactNode } from "react";

type SectionShellProps = {
  id?: string;
  className?: string;
  children: ReactNode;
};

type SectionHeadingProps = {
  kicker: string;
  title: string;
  description?: string;
  className?: string;
};

type TileProps = HTMLAttributes<HTMLElement> & {
  as?: "article" | "div" | "section";
  tone?: "default" | "accent" | "subtle";
  children: ReactNode;
};

export function SectionShell({ id, className = "", children }: SectionShellProps) {
  /** Keep landing sections aligned to one shell width while allowing distinct inner compositions. */
  return (
    <section id={id} className={`lp-section ${className}`.trim()}>
      <div className="lp-shell">{children}</div>
    </section>
  );
}

export function SectionHeading({ kicker, title, description, className = "" }: SectionHeadingProps) {
  /** Render one consistent heading block for landing groups while allowing section-specific layout around it. */
  return (
    <div className={`lp-section__heading ${className}`.trim()}>
      <span className="lp-kicker">{kicker}</span>
      <h2>{title}</h2>
      {description ? <p>{description}</p> : null}
    </div>
  );
}

export function Tile({ as = "article", tone = "default", className = "", children, ...rest }: TileProps) {
  /** Provide one reusable tile surface so sections can vary layout without rebuilding the card shell each time. */
  const Component = as;
  return (
    <Component className={`lp-tile lp-tile--${tone} ${className}`.trim()} {...rest}>
      {children}
    </Component>
  );
}
