import { render, screen } from "@testing-library/react";
import { SettingsPage } from "./SettingsPage";
import type { AuthUser } from "../types";

const user: AuthUser = {
  id: "user-1",
  email: "manager@example.com",
  role: "client_manager",
  must_change_password: false,
  client_account: {
    id: "org-1",
    name: "Acme",
    slug: "acme",
  },
};

describe("SettingsPage", () => {
  it("renders profile labels without raw role or password-status values", () => {
    render(<SettingsPage user={user} onUserUpdated={vi.fn()} />);

    expect(screen.getByText("Роль")).toBeInTheDocument();
    expect(screen.getByText("Менеджер")).toBeInTheDocument();
    expect(screen.getByText("Организация")).toBeInTheDocument();
    expect(screen.getByText("Статус пароля")).toBeInTheDocument();
    expect(screen.getByText("Актуален")).toBeInTheDocument();
    expect(screen.queryByText("Role")).not.toBeInTheDocument();
    expect(screen.queryByText("Organization")).not.toBeInTheDocument();
    expect(screen.queryByText("Password status")).not.toBeInTheDocument();
    expect(screen.queryByText("client_manager")).not.toBeInTheDocument();
    expect(screen.queryByText("ok")).not.toBeInTheDocument();
  });
});
