import type { Status } from "../api";
import { STATUS_ORDER, statusIndex } from "../format";

export function StatusSteps({ status }: { status: Status }) {
  const current = statusIndex(status);
  return (
    <ol className="steps" aria-label="Статус заявки" data-testid="status" data-status={status}>
      {STATUS_ORDER.map((s, i) => (
        <li
          key={s.status}
          className={i < current ? "done" : i === current ? "current" : ""}
          aria-current={i === current ? "step" : undefined}
        >
          <span className="step-num">{i + 1}</span>
          <span className="step-label">{s.label}</span>
        </li>
      ))}
    </ol>
  );
}
