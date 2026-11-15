import { describe, expect, it } from "bun:test";
import { currentUtm, pickUtm, withUtm } from "./utmForward";

const memory = () => {
  const values = new Map<string, string>();
  return { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => void values.set(k, v) } as unknown as Storage;
};

describe("utmForward", () => {
  it("keeps only non-empty utm_* params", () => {
    expect(pickUtm("?utm_source=tiktok&utm_content=a2&ref=x&utm_medium=")).toBe("utm_source=tiktok&utm_content=a2");
    expect(pickUtm("")).toBe("");
  });

  it("adds UTM only to admin links and leaves them intact without UTM", () => {
    expect(withUtm("https://app.barbersoftly.com/signup", "utm_source=tiktok&utm_content=a2")).toBe("https://app.barbersoftly.com/signup?utm_source=tiktok&utm_content=a2");
    expect(withUtm("https://app.barbersoftly.com/signup", "")).toBe("https://app.barbersoftly.com/signup");
    expect(withUtm("https://barbersoftly.com/pricing", "utm_source=tiktok")).toBe("https://barbersoftly.com/pricing");
    expect(withUtm("https://app.barbersoftly.com/signup?utm_source=web", "utm_source=tiktok")).toBe("https://app.barbersoftly.com/signup?utm_source=web");
  });

  it("remembers the tab's UTM across landing pages without UTM", () => {
    const storage = memory();
    expect(currentUtm("?utm_source=tiktok", storage)).toBe("utm_source=tiktok");
    expect(currentUtm("", storage)).toBe("utm_source=tiktok");
    expect(currentUtm("", null)).toBe("");
  });
});
