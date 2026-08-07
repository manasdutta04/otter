import { existsSync } from "fs";
import path from "path";

type PressSlotProps = {
  /** Filename under /public/press, e.g. Workspace-UI.png */
  file: string;
  label: string;
  caption?: string;
};

export function PressSlot({ file, label, caption }: PressSlotProps) {
  const abs = path.join(process.cwd(), "public", "press", file);
  const ready = existsSync(abs);

  if (ready) {
    return (
      <div className="press-slot press-slot-ready">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/press/${file}`} alt={label} />
        {caption ? <p className="press-slot-caption">{caption}</p> : null}
      </div>
    );
  }

  return (
    <div className="press-slot press-slot-empty" aria-label={`${label} screenshot placeholder`}>
      <div className="press-slot-chrome">
        <span />
        <span />
        <span />
      </div>
      <div className="press-slot-body">
        <p className="press-slot-kicker">Press folder</p>
        <strong>{label}</strong>
        <p className="muted">
          Add <code>public/press/{file}</code> later — this slot will show it automatically.
        </p>
      </div>
    </div>
  );
}
