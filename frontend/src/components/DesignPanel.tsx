import { useState } from "react";
import type { Design, DesignParams, Material, RequestDetail } from "../api";
import { initialParams } from "../designParams";
import { edgeLabel } from "../format";

interface Props {
  request: RequestDetail;
  design: Design | null;
  materials: Material[];
  problems: string[];
  onSave: (params: DesignParams) => Promise<void>;
}

const NUMBERS: { key: keyof DesignParams; label: string }[] = [
  { key: "width_mm", label: "Ширина, мм" },
  { key: "height_mm", label: "Высота, мм" },
  { key: "depth_mm", label: "Глубина, мм" },
  { key: "shelves", label: "Полок" },
  { key: "doors", label: "Дверей" },
];

export function DesignPanel({ request, design, materials, problems, onSave }: Props) {
  const [p, setP] = useState<DesignParams>(() => initialParams(request, design));
  const enabled = ["parsed", "designed", "estimated"].includes(request.status);
  const boards = materials.filter((m) => m.kind === "board" && m.thickness_mm === p.thickness_mm);
  const of = (kind: Material["kind"]) => materials.filter((m) => m.kind === kind);
  const handles = of("hardware").filter((m) => m.code.startsWith("HW-HANDLE"));

  function set<K extends keyof DesignParams>(key: K, value: DesignParams[K]) {
    setP((prev) => ({ ...prev, [key]: value }));
  }

  function setThickness(t: number) {
    const board = materials.find((m) => m.kind === "board" && m.thickness_mm === t);
    setP((prev) => ({ ...prev, thickness_mm: t, board_code: board?.code ?? prev.board_code }));
  }

  return (
    <section
      className={`panel ${enabled || design ? "" : "locked"}`}
      aria-labelledby="design-title"
    >
      <h2 id="design-title">2. Конструкция</h2>
      {!enabled && !design && <p className="hint">Станет доступна, когда заявка разобрана.</p>}
      {enabled && (
        <form
          className="design-form"
          onSubmit={(e) => {
            e.preventDefault();
            void onSave(p);
          }}
        >
          {NUMBERS.map(({ key, label }) => (
            <label key={key}>
              {label}
              <input
                type="number"
                inputMode="numeric"
                name={key}
                value={p[key] as number}
                onChange={(e) => set(key, Number.parseInt(e.target.value || "0", 10) as never)}
              />
            </label>
          ))}
          <label>
            Толщина плиты, мм
            <select
              name="thickness_mm"
              value={p.thickness_mm}
              onChange={(e) => setThickness(Number(e.target.value))}
            >
              <option value={16}>16</option>
              <option value={18}>18</option>
            </select>
          </label>
          <label>
            Плита
            <select
              name="board_code"
              value={p.board_code}
              onChange={(e) => set("board_code", e.target.value)}
            >
              {boards.map((m) => (
                <option key={m.code} value={m.code}>
                  {m.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Кромка
            <select
              name="edge_code"
              value={p.edge_code}
              onChange={(e) => set("edge_code", e.target.value)}
            >
              {of("edge").map((m) => (
                <option key={m.code} value={m.code}>
                  {m.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ручки
            <select
              name="handle_code"
              value={p.handle_code}
              onChange={(e) => set("handle_code", e.target.value)}
            >
              {handles.map((m) => (
                <option key={m.code} value={m.code}>
                  {m.name}
                  {m.price_kop === null ? " (нет цены)" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="check">
            <input
              type="checkbox"
              name="back_panel"
              checked={p.back_panel}
              onChange={(e) => set("back_panel", e.target.checked)}
            />
            Задняя стенка
          </label>
          <div className="actions wide">
            <button type="submit">Построить спецификацию</button>
          </div>
        </form>
      )}
      {problems.length > 0 && (
        <ul className="problems" data-testid="design-problems">
          {problems.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
      {design && (
        <>
          <h3>
            Спецификация <span className="muted">внутренний проём {design.inner_width_mm} мм</span>
          </h3>
          <div className="table-wrap">
            <table data-testid="spec">
              <thead>
                <tr>
                  <th>Деталь</th>
                  <th className="num">Длина × ширина, мм</th>
                  <th className="num">Кол-во</th>
                  <th>Материал</th>
                  <th>Кромка</th>
                </tr>
              </thead>
              <tbody>
                {design.parts.map((part) => (
                  <tr key={part.code} data-part={part.code}>
                    <td>{part.name}</td>
                    <td className="num mono">
                      {part.length_mm} × {part.width_mm}
                    </td>
                    <td className="num">{part.qty}</td>
                    <td className="mono small-text">{part.material_code}</td>
                    <td>{edgeLabel(part.edge_long, part.edge_short)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="hardware">
            Фурнитура:{" "}
            {design.hardware.map((h) => `${h.name.toLowerCase()} — ${h.qty} шт.`).join(", ")}
          </p>
        </>
      )}
    </section>
  );
}
