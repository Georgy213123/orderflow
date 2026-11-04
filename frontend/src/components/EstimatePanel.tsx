import type { Estimate, RequestDetail } from "../api";
import { formatDate, formatFactor, formatKop, formatQuantity, unitLabel } from "../format";

const KIND_LABEL: Record<string, string> = {
  board: "Плита",
  back: "Задняя стенка",
  edge: "Кромка",
  hardware: "Фурнитура",
};

interface Props {
  request: RequestDetail;
  estimate: Estimate | null;
  onCalculate: () => Promise<void>;
  onSend: () => Promise<void>;
}

export function EstimatePanel({ request, estimate, onCalculate, onSend }: Props) {
  const canCalculate = request.status === "designed" || request.status === "estimated";
  const canSend = request.status === "estimated" && estimate?.complete === true;

  return (
    <section
      className={`panel ${canCalculate || estimate ? "" : "locked"}`}
      aria-labelledby="estimate-title"
    >
      <h2 id="estimate-title">3. Смета</h2>
      {!canCalculate && !estimate && (
        <p className="hint">Станет доступна, когда готова конструкция.</p>
      )}
      {canCalculate && (
        <div className="actions">
          <button type="button" onClick={() => void onCalculate()}>
            {estimate ? "Пересчитать смету" : "Посчитать смету"}
          </button>
        </div>
      )}
      {estimate && (
        <>
          {estimate.warnings.length > 0 && (
            <ul className="problems" data-testid="estimate-warnings">
              {estimate.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
          <div className="table-wrap">
            <table data-testid="estimate">
              <thead>
                <tr>
                  <th>Позиция</th>
                  <th className="num">Нетто</th>
                  <th className="num">Запас</th>
                  <th className="num">В смету</th>
                  <th className="num">Цена</th>
                  <th>Дата цены</th>
                  <th className="num">Сумма</th>
                </tr>
              </thead>
              <tbody>
                {estimate.lines.map((ln) => (
                  <tr key={ln.material_code} className={ln.amount_kop === null ? "no-price" : ""}>
                    <td>{ln.name}</td>
                    <td className="num mono">{formatQuantity(ln.net_quantity, ln.unit)}</td>
                    <td className="num mono">×{formatFactor(ln.waste_factor)}</td>
                    <td className="num mono">
                      {formatQuantity(ln.quantity, ln.unit)} {unitLabel(ln.unit)}
                    </td>
                    <td className="num mono">
                      {ln.price_kop === null ? "нет цены" : formatKop(ln.price_kop)}
                    </td>
                    <td>{formatDate(ln.price_date)}</td>
                    <td className="num mono">
                      {ln.amount_kop === null ? "—" : formatKop(ln.amount_kop)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                {Object.entries(estimate.totals_by_kind).map(([kind, kop]) => (
                  <tr key={kind} className="subtotal">
                    <td colSpan={6}>{KIND_LABEL[kind] ?? kind}</td>
                    <td className="num mono">{formatKop(kop)}</td>
                  </tr>
                ))}
                <tr className="total">
                  <td colSpan={6}>Итого{estimate.complete ? "" : " (неполный)"}</td>
                  <td className="num mono" data-testid="estimate-total">
                    {formatKop(estimate.total_kop)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
          {request.status !== "sent" && (
            <div className="actions">
              <button type="button" disabled={!canSend} onClick={() => void onSend()}>
                Отправить клиенту
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
