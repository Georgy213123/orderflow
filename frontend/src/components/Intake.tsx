import { useState } from "react";
import type { FieldKey, RequestDetail } from "../api";
import { FIELD_ORDER } from "../format";
import { FieldRow } from "./FieldRow";

const REQUIRED = new Set<FieldKey>([
  "product_type",
  "width_mm",
  "height_mm",
  "depth_mm",
  "client_name",
  "phone",
]);

interface Props {
  request: RequestDetail | null;
  onCreate: (text: string) => Promise<void>;
  onSaveField: (key: FieldKey, value: string) => Promise<void>;
  onMarkParsed: () => Promise<void>;
}

export function Intake({ request, onCreate, onSaveField, onMarkParsed }: Props) {
  const [text, setText] = useState("");

  if (!request) {
    return (
      <section className="panel" aria-labelledby="intake-title">
        <h2 id="intake-title">1. Заявка</h2>
        <p className="hint">
          Вставьте текст из письма или мессенджера. Найденное в тексте придёт как предположение: его
          нужно подтвердить. Пустой текст — заполнить поля вручную.
        </p>
        <label htmlFor="raw-text" className="sr-only">
          Текст заявки
        </label>
        <textarea
          id="raw-text"
          rows={6}
          value={text}
          placeholder="Например: нужен шкаф 1200х2100х600 мм, 4 полки, две двери. Меня зовут…"
          onChange={(e) => setText(e.target.value)}
        />
        <div className="actions">
          <button type="button" onClick={() => void onCreate(text)}>
            {text.trim() ? "Разобрать текст" : "Заполнить вручную"}
          </button>
        </div>
      </section>
    );
  }

  const byKey = new Map(request.fields.map((f) => [f.key, f]));
  const editable = request.status === "new";

  return (
    <section className="panel" aria-labelledby="intake-title">
      <h2 id="intake-title">1. Заявка №{request.id}</h2>
      {request.raw_text && (
        <details className="raw">
          <summary>Исходный текст</summary>
          <p>{request.raw_text}</p>
        </details>
      )}
      <div className="fields">
        {FIELD_ORDER.map((def) => {
          const field = byKey.get(def.key);
          return (
            <FieldRow
              key={`${def.key}-${field?.value ?? ""}-${field?.confirmed ?? ""}`}
              def={def}
              field={field}
              required={REQUIRED.has(def.key)}
              editable={editable}
              onSave={onSaveField}
            />
          );
        })}
      </div>
      {editable && (
        <>
          {request.missing.length > 0 && (
            <ul className="problems" data-testid="missing">
              {request.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
          <div className="actions">
            <button
              type="button"
              disabled={request.missing.length > 0}
              onClick={() => void onMarkParsed()}
            >
              Заявка разобрана
            </button>
          </div>
        </>
      )}
    </section>
  );
}
