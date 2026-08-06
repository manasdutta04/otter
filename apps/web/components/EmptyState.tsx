import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  detail?: string;
  action?: ReactNode;
};

export function EmptyState({ title, detail, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p className="empty-title">{title}</p>
      {detail ? <p className="empty-detail">{detail}</p> : null}
      {action ? <div className="empty-action">{action}</div> : null}
    </div>
  );
}
