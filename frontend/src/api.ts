export type Status = "new" | "parsed" | "designed" | "estimated" | "sent";
export type FieldSource = "text" | "human";
export type FieldKey =
  | "product_type"
  | "width_mm"
  | "height_mm"
  | "depth_mm"
  | "shelves"
  | "doors"
  | "client_name"
  | "phone"
  | "email";

export interface Field {
  key: FieldKey;
  label: string;
  value: string;
  source: FieldSource;
  confirmed: boolean;
  fragment: string | null;
  required: boolean;
}

export interface RequestDetail {
  id: number;
  raw_text: string;
  status: Status;
  status_label: string;
  parser: string;
  created_at: string;
  fields: Field[];
  missing: string[];
}

export interface RequestSummary {
  id: number;
  status: Status;
  status_label: string;
  client_name: string | null;
  product_type: string | null;
  created_at: string;
}

export interface DesignParams {
  width_mm: number;
  height_mm: number;
  depth_mm: number;
  thickness_mm: number;
  shelves: number;
  doors: number;
  back_panel: boolean;
  board_code: string;
  edge_code: string;
  back_code: string;
  handle_code: string;
}

export interface Part {
  code: string;
  name: string;
  length_mm: number;
  width_mm: number;
  qty: number;
  material_code: string;
  edge_long: number;
  edge_short: number;
}

export interface Design {
  request_id: number;
  params: DesignParams;
  inner_width_mm: number;
  parts: Part[];
  hardware: { material_code: string; name: string; qty: number }[];
}

export interface EstimateLine {
  kind: string;
  material_code: string;
  name: string;
  unit: string;
  net_quantity: string;
  waste_factor: string;
  quantity: string;
  price_kop: number | null;
  price_date: string | null;
  amount_kop: number | null;
}

export interface Estimate {
  request_id: number;
  lines: EstimateLine[];
  totals_by_kind: Record<string, number>;
  total_kop: number;
  total_formatted: string;
  complete: boolean;
  warnings: string[];
}

export interface Material {
  code: string;
  name: string;
  kind: "board" | "back" | "edge" | "hardware";
  unit: string;
  thickness_mm: number | null;
  price_kop: number | null;
  price_date: string | null;
  waste_factor: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public problems: string[] = [],
  ) {
    super(message);
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const p = data as { message?: string; problems?: string[] };
    throw new ApiError(res.status, p.message ?? `ошибка ${res.status}`, p.problems ?? []);
  }
  return data as T;
}

export const api = {
  materials: () => call<Material[]>("GET", "/materials"),
  listRequests: () => call<RequestSummary[]>("GET", "/requests"),
  getRequest: (id: number) => call<RequestDetail>("GET", `/requests/${id}`),
  createRequest: (raw_text: string, fields: Partial<Record<FieldKey, string>> = {}) =>
    call<RequestDetail>("POST", "/requests", { raw_text, fields }),
  updateField: (id: number, key: FieldKey, value: string) =>
    call<RequestDetail>("PUT", `/requests/${id}/fields/${key}`, { value }),
  transition: (id: number, to: Status) =>
    call<RequestDetail>("POST", `/requests/${id}/transition`, { to }),
  getDesign: (id: number) => call<Design>("GET", `/requests/${id}/design`),
  saveDesign: (id: number, params: DesignParams) =>
    call<Design>("PUT", `/requests/${id}/design`, params),
  getEstimate: (id: number) => call<Estimate>("GET", `/requests/${id}/estimate`),
  calculateEstimate: (id: number) => call<Estimate>("POST", `/requests/${id}/estimate`),
};
