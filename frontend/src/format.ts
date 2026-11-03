import type { FieldKey, FieldSource, Status } from "./api";

export const FIELD_ORDER: {
  key: FieldKey;
  label: string;
  inputMode?: "numeric" | "tel" | "email";
}[] = [
  { key: "product_type", label: "Изделие" },
  { key: "width_mm", label: "Ширина, мм", inputMode: "numeric" },
  { key: "height_mm", label: "Высота, мм", inputMode: "numeric" },
  { key: "depth_mm", label: "Глубина, мм", inputMode: "numeric" },
  { key: "shelves", label: "Полок", inputMode: "numeric" },
  { key: "doors", label: "Дверей", inputMode: "numeric" },
  { key: "client_name", label: "Клиент" },
  { key: "phone", label: "Телефон", inputMode: "tel" },
  { key: "email", label: "Почта", inputMode: "email" },
];

export const STATUS_ORDER: { status: Status; label: string }[] = [
  { status: "new", label: "Новая" },
  { status: "parsed", label: "Разобрана" },
  { status: "designed", label: "Конструкция готова" },
  { status: "estimated", label: "Смета готова" },
  { status: "sent", label: "Отправлена клиенту" },
];

export function statusIndex(s: Status): number {
  return STATUS_ORDER.findIndex((x) => x.status === s);
}

export function sourceLabel(source: FieldSource): string {
  return source === "text" ? "найдено в тексте" : "ввёл человек";
}

/** 1233196 → «12 331,96 ₽». Деньги приходят в копейках целым числом. */
export function formatKop(kop: number): string {
  const sign = kop < 0 ? "-" : "";
  const abs = Math.abs(kop);
  const rub = Math.floor(abs / 100)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const k = (abs % 100).toString().padStart(2, "0");
  return `${sign}${rub},${k} ₽`;
}

const UNIT: Record<string, string> = { m2: "м²", m: "м", pcs: "шт." };

export function unitLabel(unit: string): string {
  return UNIT[unit] ?? unit;
}

/** «10.49» → «10,49». Количества приходят строкой (Decimal), в число не переводим. */
export function formatQty(q: string): string {
  return q.replace(/\.0+$|(\.\d*?)0+$/, "$1").replace(".", ",");
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

export function edgeLabel(long: number, short: number): string {
  if (!long && !short) return "—";
  return [long ? `${long} дл.` : "", short ? `${short} кор.` : ""].filter(Boolean).join(" + ");
}
