import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatBubble } from "@/features/assistant/components/ChatBubble";

describe("ChatBubble", () => {
  it("renders a user message", () => {
    render(<ChatBubble message={{ role: "user", content: "What is my highest risk medicine?" }} />);
    expect(screen.getByText("What is my highest risk medicine?")).toBeInTheDocument();
  });

  it("renders an assistant message", () => {
    render(<ChatBubble message={{ role: "assistant", content: "Insulin, at Hospital A." }} />);
    expect(screen.getByText("Insulin, at Hospital A.")).toBeInTheDocument();
  });

  it("shows a pending state distinctly while a response is in flight", () => {
    render(<ChatBubble message={{ role: "assistant", content: "Thinking…" }} pending />);
    expect(screen.getByText("Thinking…")).toHaveClass("italic");
  });
});
