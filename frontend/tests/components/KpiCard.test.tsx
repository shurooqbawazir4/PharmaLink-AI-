import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { KpiCard, KpiCardEmpty } from "@/components/charts/KpiCard";

describe("KpiCard", () => {
  it("renders the label, value, and hint", () => {
    render(<KpiCard label="Stockouts" value="3" hint="down from 5 last week" tone="positive" />);

    expect(screen.getByText("Stockouts")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("down from 5 last week")).toBeInTheDocument();
  });

  it("omits the hint line when none is given", () => {
    render(<KpiCard label="Stockouts" value="0" />);

    expect(screen.getByText("Stockouts")).toBeInTheDocument();
    expect(screen.queryByText(/down from/)).not.toBeInTheDocument();
  });
});

describe("KpiCardEmpty", () => {
  it("renders an honest 'not enough data yet' state instead of a fabricated number", () => {
    render(<KpiCardEmpty label="Forecast accuracy" reason="No elapsed history to compare against yet." />);

    expect(screen.getByText("Forecast accuracy")).toBeInTheDocument();
    expect(screen.getByText("Not enough data yet")).toBeInTheDocument();
    expect(screen.getByText("No elapsed history to compare against yet.")).toBeInTheDocument();
  });
});
