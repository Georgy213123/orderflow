import type { RequestSummary } from "../api";

interface Props {
  items: RequestSummary[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

export function RequestList({ items, selectedId, onSelect }: Props) {
  return (
    <nav className="request-list" aria-label="Заявки">
      <button
        type="button"
        className={`new-request ${selectedId === null ? "active" : ""}`}
        onClick={() => onSelect(null)}
      >
        + Новая заявка
      </button>
      <ul>
        {items.map((r) => (
          <li key={r.id}>
            <button
              type="button"
              className={r.id === selectedId ? "active" : ""}
              onClick={() => onSelect(r.id)}
            >
              <span className="rl-title">
                №{r.id} · {r.product_type ?? "изделие не указано"}
              </span>
              <span className="rl-meta">
                {r.client_name ?? "клиент не указан"} —{" "}
                <span className={`st st-${r.status}`}>{r.status_label}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
