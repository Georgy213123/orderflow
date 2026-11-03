import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

/** Находки ревью R-02 и R-04: состояние экрана при переключении заявок. */

function req(id: number) {
  return {
    id,
    raw_text: "",
    status: "designed",
    status_label: "конструкция готова",
    parser: "rules",
    created_at: "2026-11-01T10:00:00Z",
    missing: [],
    fields: [],
  };
}

function design(id: number, width: number) {
  return {
    request_id: id,
    inner_width_mm: width - 32,
    params: {
      width_mm: width,
      height_mm: 2000,
      depth_mm: 500,
      thickness_mm: 16,
      shelves: 0,
      doors: 0,
      back_panel: true,
      board_code: "LDSP16-WHITE",
      edge_code: "EDGE04-WHITE",
      back_code: "HDF3-WHITE",
      handle_code: "HW-HANDLE",
    },
    parts: [],
    hardware: [],
  };
}

const WIDTH: Record<number, number> = { 1: 800, 2: 1200 };
const summaries = [1, 2].map((id) => ({
  id,
  status: "designed",
  status_label: "конструкция готова",
  client_name: `Клиент ${id}`,
  product_type: "шкаф",
  created_at: "2026-11-01T10:00:00Z",
}));

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

interface Delay {
  id: number;
  gate: Promise<void>;
  path?: "" | "/design";
}

function mockApi(delayRequest?: Delay) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const m = url.match(/^\/api\/requests\/(\d+)(\/design|\/estimate)?$/);
      if (url === "/api/materials") return json([]);
      if (url === "/api/requests") return json(summaries);
      if (!m) return json({ message: "нет" }, 404);
      const id = Number(m[1]);
      if (m[2] === "/estimate") return json({ message: "смета не найдена" }, 404);
      if (delayRequest && delayRequest.id === id && (delayRequest.path ?? "") === (m[2] ?? ""))
        await delayRequest.gate;
      if (m[2] === "/design") return json(design(id, WIDTH[id] ?? 0));
      return json(req(id));
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("App: переключение заявок", () => {
  it("R-02: форма конструкции показывает параметры открытой заявки, а не предыдущей", async () => {
    let open!: () => void;
    const gate = new Promise<void>((r) => (open = r));
    mockApi({ id: 2, gate, path: "/design" });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /№1/ }));
    await screen.findByRole("heading", { name: "1. Заявка №1" });
    await waitFor(() => expect(screen.getByLabelText("Ширина, мм")).toHaveValue(800));

    await userEvent.click(screen.getByRole("button", { name: /№2/ }));
    // Пока конструкция №2 грузится, конструкции и заявки №1 на экране быть не должно.
    expect(screen.queryByText(/внутренний проём 768 мм/)).toBeNull();
    expect(screen.queryByRole("heading", { name: "1. Заявка №1" })).toBeNull();
    open();
    await screen.findByRole("heading", { name: "1. Заявка №2" });
    await waitFor(() => expect(screen.getByText(/внутренний проём 1168 мм/)).toBeInTheDocument());
    const form = document.querySelector("form.design-form") as HTMLElement;
    expect(within(form).getByLabelText("Ширина, мм")).toHaveValue(1200);
  });

  it("R-04: запоздавший ответ по прежней заявке не подменяет открытую", async () => {
    let open!: () => void;
    const gate = new Promise<void>((r) => (open = r));
    mockApi({ id: 1, gate });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /№1/ }));
    await userEvent.click(screen.getByRole("button", { name: /№2/ }));
    await screen.findByRole("heading", { name: "1. Заявка №2" });
    open();
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByRole("heading", { name: /1\. Заявка №/ })).toHaveTextContent("№2");
    expect(screen.getByRole("button", { name: /№2/ })).toHaveClass("active");
  });
});
