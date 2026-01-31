import { describe, expect, it } from "vitest";
import { backendApiUrl } from "./backendProxy";

describe("backendApiUrl", () => {
  it("joins segments under /api", () => {
    expect(backendApiUrl(["auth", "login"], "?x=1")).toMatch(/\/api\/auth\/login\?x=1$/);
  });

  it("handles empty segments as /api root", () => {
    expect(backendApiUrl([], "")).toMatch(/\/api$/);
  });
});
