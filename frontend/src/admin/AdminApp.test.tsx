import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { AdminApp } from "./AdminApp";
import type { AuthUser } from "../types";

vi.mock("./AdminLayout", () => ({
  AdminLayout: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock("./AdminDashboard", () => ({
  AdminDashboard: () => <div>dashboard</div>,
}));

vi.mock("./OrganizationsPage", () => ({
  OrganizationsPage: () => <div>organizations</div>,
}));

vi.mock("./HistoryPage", () => ({
  HistoryPage: () => <div>history</div>,
}));

vi.mock("./AuditLogPage", () => ({
  AuditLogPage: () => <div>audit</div>,
}));

vi.mock("./UserAnalyticsPage", () => ({
  AdminUserAnalyticsPage: () => <div>user analytics</div>,
}));

vi.mock("./OrganizationDetailPage", () => ({
  OrganizationDetailPage: ({
    initialTab,
  }: {
    organizationId: string;
    initialTab?: "overview" | "users" | "configs" | "history" | "usage" | "audit";
    onNavigate: (path: string) => void;
  }) => <div>{initialTab === "users" ? "Пользователи" : "Обзор"}</div>,
}));

const internalAdmin: AuthUser = {
  id: "admin-1",
  email: "admin@example.com",
  role: "internal_admin",
  must_change_password: false,
  client_account: {
    id: "platform",
    name: "Platform",
    slug: "platform",
  },
};

describe("AdminApp organization tab routing", () => {
  it("opens organization detail on the users tab when ?tab=users is present", () => {
    render(<AdminApp user={internalAdmin} path="/admin/organizations/org-1?tab=users" onNavigate={vi.fn()} onLogout={vi.fn()} />);

    expect(screen.getByText("Пользователи")).toBeInTheDocument();
    expect(screen.queryByText("Обзор")).not.toBeInTheDocument();
  });
});
