import { parseClientPath } from "./utils";

describe("parseClientPath", () => {
  it("ignores query strings when extracting route params", () => {
    expect(parseClientPath("/app/history/session-1?from=dashboard")).toEqual({
      route: "history-detail",
      sessionId: "session-1",
    });
    expect(parseClientPath("/app/team/user-1?tab=history")).toEqual({
      route: "team-detail",
      userId: "user-1",
    });
  });
});
