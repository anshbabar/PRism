import { describe, expect, it } from "vitest";

import {
  bandColor,
  bandFromScore,
  bandLabel,
  humanizeCategory,
  percent,
} from "./format";

describe("bandFromScore", () => {
  it("maps score ranges to bands", () => {
    expect(bandFromScore(1)).toBe("low");
    expect(bandFromScore(2)).toBe("low");
    expect(bandFromScore(3)).toBe("medium");
    expect(bandFromScore(4)).toBe("high");
    expect(bandFromScore(5)).toBe("high");
  });
});

describe("bandLabel", () => {
  it("capitalizes the band", () => {
    expect(bandLabel("low")).toBe("Low");
    expect(bandLabel("medium")).toBe("Medium");
    expect(bandLabel("high")).toBe("High");
  });
});

describe("bandColor", () => {
  it("returns a distinct color per band", () => {
    const colors = new Set([bandColor("low"), bandColor("medium"), bandColor("high")]);
    expect(colors.size).toBe(3);
  });
});

describe("percent", () => {
  it("renders a 0..1 value as a rounded percentage", () => {
    expect(percent(0.482)).toBe("48%");
    expect(percent(1)).toBe("100%");
    expect(percent(0)).toBe("0%");
  });
});

describe("humanizeCategory", () => {
  it("title-cases snake_case categories", () => {
    expect(humanizeCategory("db_schema")).toBe("Db Schema");
    expect(humanizeCategory("missing_tests")).toBe("Missing Tests");
    expect(humanizeCategory("auth")).toBe("Auth");
  });
});
