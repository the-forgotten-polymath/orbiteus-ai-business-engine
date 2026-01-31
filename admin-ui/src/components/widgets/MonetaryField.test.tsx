import { describe, expect, it } from "vitest";
import { MonetaryCell } from "./MonetaryField";

/**
 * `MonetaryCell` returns a string (not a JSX element) so we can test
 * it as a pure function without spinning up the React renderer.
 */
describe("MonetaryCell", () => {
  it("formats a number with the supplied currency code", () => {
    const out = MonetaryCell({ value: 65000, currencyCode: "PLN" });
    // Locale-dependent grouping, but the value + code MUST be present.
    expect(out).toMatch(/65[ ,.\u00A0]000[\.,]00/);
    expect(out).toContain("PLN");
  });

  it("falls back to PLN when currencyCode is missing", () => {
    const out = MonetaryCell({ value: 1000 });
    expect(out).toContain("PLN");
  });

  it("renders an em-dash for null/empty/undefined", () => {
    expect(MonetaryCell({ value: null })).toBe("—");
    expect(MonetaryCell({ value: "" })).toBe("—");
    expect(MonetaryCell({ value: undefined })).toBe("—");
  });

  it("respects a custom emptyPlaceholder", () => {
    expect(
      MonetaryCell({ value: null, emptyPlaceholder: "(none)" })
    ).toBe("(none)");
  });

  it("returns the original value when input is non-numeric", () => {
    expect(MonetaryCell({ value: "hello" })).toBe("hello");
  });

  it("formats two decimals even for round amounts", () => {
    const out = MonetaryCell({ value: 50000, currencyCode: "EUR" });
    expect(out).toMatch(/50[ ,.\u00A0]000[\.,]00/);
  });

  it("falls back to plain number + suffix on bogus ISO code", () => {
    const out = MonetaryCell({ value: 12.5, currencyCode: "ZZZ" });
    // Either Intl threw → fallback path: "12.50 ZZZ"
    // or it accepted ZZZ → "ZZZ\u00A012.50".  Both must contain "12" + "ZZZ".
    expect(out).toContain("12");
    expect(out).toContain("ZZZ");
  });
});
