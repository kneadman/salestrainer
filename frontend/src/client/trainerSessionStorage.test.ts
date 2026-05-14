import {
  clearTrainerSessionRestoreState,
  getStoredTrainerSessionId,
  getTrainerSessionStorageKey,
  storeTrainerSessionId,
} from "./trainerSessionStorage";

describe("trainer session storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and reads trainer session ids under a user-scoped key", () => {
    storeTrainerSessionId("user-1", "session-1");

    expect(getTrainerSessionStorageKey("user-1")).toBe("salestrainer.currentSessionId.user-1");
    expect(getStoredTrainerSessionId("user-1")).toBe("session-1");
    expect(getStoredTrainerSessionId("user-2")).toBeNull();
  });

  it("removes legacy and current user restore state on logout cleanup", () => {
    localStorage.setItem("salestrainer.currentSessionId", "legacy-session");
    localStorage.setItem("salestrainer.currentSessionId.user-1", "session-1");
    localStorage.setItem("salestrainer.currentSessionId.user-2", "session-2");

    clearTrainerSessionRestoreState("user-1");

    expect(localStorage.getItem("salestrainer.currentSessionId")).toBeNull();
    expect(localStorage.getItem("salestrainer.currentSessionId.user-1")).toBeNull();
    expect(localStorage.getItem("salestrainer.currentSessionId.user-2")).toBe("session-2");
  });
});
