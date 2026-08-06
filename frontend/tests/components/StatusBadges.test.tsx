import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  AlertSeverityBadge,
  PurchaseOrderStatusBadge,
  RecommendedByBadge,
  TransferStatusBadge,
} from "@/components/charts/StatusBadges";

describe("AlertSeverityBadge", () => {
  it("always pairs the color with a text label — never color alone", () => {
    render(<AlertSeverityBadge severity="critical" />);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("renders warning and info distinctly", () => {
    const { rerender } = render(<AlertSeverityBadge severity="warning" />);
    expect(screen.getByText("Warning")).toBeInTheDocument();

    rerender(<AlertSeverityBadge severity="info" />);
    expect(screen.getByText("Info")).toBeInTheDocument();
  });
});

describe("TransferStatusBadge", () => {
  it("renders the status text with underscores replaced by spaces", () => {
    render(<TransferStatusBadge status="in_transit" />);
    expect(screen.getByText("in transit")).toBeInTheDocument();
  });
});

describe("PurchaseOrderStatusBadge", () => {
  it("renders the raw status label", () => {
    render(<PurchaseOrderStatusBadge status="recommended" />);
    expect(screen.getByText("recommended")).toBeInTheDocument();
  });
});

describe("RecommendedByBadge", () => {
  it("distinguishes AI-recommended from manual", () => {
    const { rerender } = render(<RecommendedByBadge recommendedBy="ai" />);
    expect(screen.getByText("AI")).toBeInTheDocument();

    rerender(<RecommendedByBadge recommendedBy="manual" />);
    expect(screen.getByText("Manual")).toBeInTheDocument();
  });
});
