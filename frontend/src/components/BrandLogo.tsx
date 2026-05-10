type BrandLogoProps = {
  title: string;
  subtitle?: string;
  className?: string;
  imageClassName?: string;
  textClassName?: string;
};

export function BrandLogo({ title, subtitle, className, imageClassName, textClassName }: BrandLogoProps) {
  /** Render one shared product logo block so landing and cabinets stay visually consistent. */
  return (
    <div className={className}>
      <img className={imageClassName} src="/logo.png" alt="" aria-hidden="true" />
      <div className={textClassName}>
        <strong>{title}</strong>
        {subtitle ? <small>{subtitle}</small> : null}
      </div>
    </div>
  );
}
