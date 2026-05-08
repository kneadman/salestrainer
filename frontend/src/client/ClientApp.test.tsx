import { render, screen } from "@testing-library/react";
import { ClientApp } from "./ClientApp";
import type { AuthUser } from "../types";

const managerUser: AuthUser = {
  id: "user-1",
  email: "manager@example.com",
  role: "client_manager",
  must_change_password: false,
  client_account: {
    id: "account-1",
    name: "Acme",
    slug: "acme",
  },
};

describe("ClientApp", () => {
  it("shows a human-readable no-access message for lead-only sections", () => {
    render(
      <ClientApp
        user={managerUser}
        path="/app/team"
        onNavigate={vi.fn()}
        onLogout={vi.fn().mockResolvedValue(undefined)}
        onUserUpdated={vi.fn()}
      />,
    );

    expect(screen.getByText("Командные разделы доступны только руководителю команды.")).toBeInTheDocument();
    expect(screen.queryByText("client_lead")).not.toBeInTheDocument();
  });
});
