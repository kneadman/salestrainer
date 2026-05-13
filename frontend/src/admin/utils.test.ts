import { auditPayloadSummary, parseAdminPath } from "./utils";

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

describe("auditPayloadSummary", () => {
  it("summarizes safe audit payload fields without raw ids or JSON syntax", () => {
    const summary = auditPayloadSummary({
      email: "manager@example.com",
      name: "Первичный контакт",
      client_slug: "acme",
      default: true,
      actor_user_id: "user-1",
      entity_id: "entity-1",
      client_account_id: "org-1",
    });

    expect(summary).toContain("Пользователь: manager@example.com");
    expect(summary).toContain("Настройка: Первичный контакт");
    expect(summary).toContain("Организация: acme");
    expect(summary).toContain("Назначена по умолчанию");
    expect(summary).not.toContain("user-1");
    expect(summary).not.toContain("entity-1");
    expect(summary).not.toContain("org-1");
    expect(summary).not.toContain("{");
  });

  it("returns a neutral empty-state label for id-only payloads", () => {
    expect(auditPayloadSummary({ actor_user_id: "user-1", entity_id: "entity-1" })).toBe("Без дополнительных данных");
  });
});
