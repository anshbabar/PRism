import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RiskBadge } from "./RiskBadge";

describe("RiskBadge", () => {
  it("renders the band label and score", () => {
    render(<RiskBadge band="high" score={4} />);
    expect(screen.getByText(/High/)).toBeInTheDocument();
    expect(screen.getByText(/4\/5/)).toBeInTheDocument();
  });

  it("omits the score when not provided", () => {
    const { container } = render(<RiskBadge band="low" />);
    expect(container.textContent).toContain("Low");
    expect(container.textContent).not.toContain("/5");
  });

  it("renders a colored status dot", () => {
    const { container } = render(<RiskBadge band="medium" score={3} />);
    expect(container.querySelector(".risk-dot")).not.toBeNull();
  });
});
