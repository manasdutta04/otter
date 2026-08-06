import Link from "next/link";

type BrandProps = {
  /** Pass `null` for a non-linking mark (e.g. landing hero). */
  href?: string | null;
  size?: "sm" | "md" | "lg" | "hero";
  showWordmark?: boolean;
};

const SIZE_CLASS: Record<NonNullable<BrandProps["size"]>, string> = {
  sm: "brand brand-sm",
  md: "brand brand-md",
  lg: "brand brand-lg",
  hero: "brand brand-hero",
};

export function Brand({ href = "/", size = "md", showWordmark = true }: BrandProps) {
  const className = SIZE_CLASS[size];
  const content = (
    <>
      <span className="brand-emoji" aria-hidden="true">
        🦦
      </span>
      {showWordmark ? <span className="brand-word">otter</span> : null}
    </>
  );

  if (href === null) {
    return <span className={className}>{content}</span>;
  }

  return (
    <Link className={className} href={href}>
      {content}
    </Link>
  );
}
