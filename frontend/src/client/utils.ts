import type { ClientRouteState } from "./types";

export function parseClientPath(path: string): ClientRouteState {
  /** Convert /app browser paths to the lightweight client route state. */
  const [pathname] = path.split("?");
  const segments = pathname.split("/").filter(Boolean);
  if (segments[0] !== "app") {
    return { route: "dashboard" };
  }
  if (segments[1] === "trainer") {
    return { route: "trainer" };
  }
  if (segments[1] === "history" && segments[2]) {
    return { route: "history-detail", sessionId: segments[2] };
  }
  if (segments[1] === "history") {
    return { route: "history" };
  }
  if (segments[1] === "analytics") {
    return { route: "analytics" };
  }
  if (segments[1] === "team" && segments[2]) {
    return { route: "team-detail", userId: segments[2] };
  }
  if (segments[1] === "team") {
    return { route: "team" };
  }
  if (segments[1] === "team-analytics") {
    return { route: "team-analytics" };
  }
  if (segments[1] === "balance") {
    return { route: "balance" };
  }
  if (segments[1] === "settings") {
    return { route: "settings" };
  }
  return { route: "dashboard" };
}
