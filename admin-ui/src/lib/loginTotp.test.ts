import { describe, expect, it } from "vitest";
import { loginNeedsTotpStep } from "./loginTotp";

describe("loginNeedsTotpStep", () => {
  it("returns true only when the backend sets requires_totp", () => {
    expect(loginNeedsTotpStep({ requires_totp: true })).toBe(true);
    expect(loginNeedsTotpStep({ requires_totp: false })).toBe(false);
    expect(loginNeedsTotpStep({})).toBe(false);
  });
});
