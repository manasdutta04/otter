import Link from "next/link";

type BrandProps = {
  href?: string | null;
  size?: "sm" | "md" | "lg";
};

const SIZE_CLASS: Record<NonNullable<BrandProps["size"]>, string> = {
  sm: "brand brand-sm",
  md: "brand brand-md",
  lg: "brand brand-lg",
};

export function Brand({ href = "/", size = "md" }: BrandProps) {
  const className = SIZE_CLASS[size];
  const content = (
    <>
      <span className="brand-emoji" aria-hidden="true">
        🦦
      </span>
      <span className="brand-word">otter</span>
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
