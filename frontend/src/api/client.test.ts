import { describe, expect, it } from "vitest";
import { authStore } from "./client";

describe("authStore", () => {
  it("stores and clears tokens", () => {
    authStore.set({ access_token: "abc", refresh_token: "xyz" });
    expect(authStore.token).toBe("abc");
    expect(authStore.refresh).toBe("xyz");
    authStore.clear();
    expect(authStore.token).toBeNull();
  });
});

describe("api surface", () => {
  it("exposes all required endpoint groups", async () => {
    const { api } = await import("./client");
    const groups = ["login", "projects", "createProject", "uploadDataset", "createAnalysis", "differentialExpression",
      "enrichment", "network", "trainML", "drugPipeline", "generateReport", "assistantChat", "manuscript", "adminUsers"];
    for (const g of groups) {
      expect(typeof api[g as keyof typeof api]).toBe("function");
    }
  });
});
