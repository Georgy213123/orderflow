import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusSteps } from "./StatusSteps";

describe("StatusSteps (US-05)", () => {
  it("текущий шаг отмечен, предыдущие пройдены", () => {
    render(<StatusSteps status="designed" />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(items[2]).toHaveAttribute("aria-current", "step");
    expect(items[2]).toHaveTextContent("Конструкция готова");
    expect(items[0]).toHaveClass("done");
    expect(items[3]).not.toHaveClass("done");
  });
});
