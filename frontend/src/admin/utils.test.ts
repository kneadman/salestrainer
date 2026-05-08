import { parseAdminPath } from "./utils";

describe("parseAdminPath", () => {
  it("parses an organization detail route with users tab query", () => {
    expect(parseAdminPath("/admin/organizations/org-1?tab=users")).toEqual({
      route: "organization-detail",
      organizationId: "org-1",
      tab: "users",
    });
  });

  it("keeps organization detail route without tab when query is absent", () => {
    expect(parseAdminPath("/admin/organizations/org-1")).toEqual({
      route: "organization-detail",
      organizationId: "org-1",
      tab: undefined,
    });
  });

  it("parses organization user analytics route before generic organization detail", () => {
    expect(parseAdminPath("/admin/organizations/org-1/users/user-1/analytics")).toEqual({
      route: "organization-user-analytics",
      organizationId: "org-1",
      userId: "user-1",
    });
  });
});
