import { useState } from "react";
import type { Field, FieldKey } from "../api";
import { sourceLabel } from "../format";

interface Props {
  def: { key: FieldKey; label: string; inputMode?: "numeric" | "tel" | "email" };
  field?: Field;
  required: boolean;
  editable: boolean;
  onSave: (key: FieldKey, value: string) => Promise<void>;
}

export function FieldRow({ def, field, required, editable, onSave }: Props) {
  const [value, setValue] = useState(field?.value ?? "");
  const [busy, setBusy] = useState(false);
  const changed = value.trim() !== (field?.value ?? "");
  const id = `field-${def.key}`;

  const state = !field ? "empty" : field.confirmed ? "confirmed" : "guess";
  // Необязательное поле можно убрать, оставив пустым (R-08 ревью).
  const clearing = changed && value.trim() === "" && !required;
  const action = clearing ? "Убрать" : changed ? "Сохранить" : "Подтвердить";
  const canAct =
    editable && !busy && (value.trim() !== "" || clearing) && (changed || state === "guess");

  async function act() {
    setBusy(true);
    try {
      await onSave(def.key, value);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`field-row ${state}`} data-testid={id} data-state={state}>
      <label htmlFor={id}>
        {def.label}
        {required && (
          <span className="req" aria-label="обязательное">
            {" "}
            *
          </span>
        )}
      </label>
      <input
        id={id}
        value={value}
        inputMode={def.inputMode}
        disabled={!editable}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && canAct) void act();
        }}
      />
      <div className="field-meta">
        {field && (
          <span className={`badge source-${field.source}`} data-testid={`${id}-source`}>
            {sourceLabel(field.source)}
          </span>
        )}
        {field && !field.confirmed && <span className="badge pending">не подтверждено</span>}
        {field?.confirmed && !changed && <span className="badge ok">подтверждено</span>}
        {field?.fragment && field.source === "text" && (
          <span className="fragment" title="Фрагмент исходного текста">
            «{field.fragment}»
          </span>
        )}
      </div>
      {editable && (
        <button type="button" className="small" disabled={!canAct} onClick={() => void act()}>
          {action}
        </button>
      )}
    </div>
  );
}
