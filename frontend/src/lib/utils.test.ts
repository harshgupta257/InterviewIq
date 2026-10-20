import { describe, expect, it } from "vitest";
import { formatPct, safeRedirectPath, scoreBand } from "./utils";

describe("score helpers", () => {
  it("formats percentages and missing values", () => {
    expect(formatPct(80)).toBe("80%");
    expect(formatPct(75.44, 1)).toBe("75.4%");
    expect(formatPct(null)).toBe("—");
  });

  it("bands scores", () => {
    expect(scoreBand(80).tone).toBe("good");
    expect(scoreBand(65).tone).toBe("ok");
    expect(scoreBand(40).label).toBe("Needs work");
  });
});

describe("safeRedirectPath", () => {
  it("allows relative paths", () => {
    expect(safeRedirectPath("/history?page=2")).toBe("/history?page=2");
  });
  it.each(["//evil.com", String.raw`/\evil.com`, "https://evil.com", "javascript:alert(1)", `/${String.fromCharCode(9)}x`, "", null])(
    "rejects %s",
    (v) => {
      expect(safeRedirectPath(v)).toBeNull();
    },
  );
});
