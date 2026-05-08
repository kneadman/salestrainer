import { parseAdminPath } from "./utils";

describe("parseAdminPath", () => {
  it("parses organization user analytics route before generic organization detail", () => {
    expect(parseAdminPath("/admin/organizations/org-1/users/user-1/analytics")).toEqual({
      route: "organization-user-analytics",
      organizationId: "org-1",
      userId: "user-1",
    });
  });
});
