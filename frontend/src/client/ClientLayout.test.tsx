import { render } from "@testing-library/react";
import { ClientLayout } from "./ClientLayout";
import type { AuthUser } from "../types";

const user: AuthUser = {
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

describe("ClientLayout", () => {
  it("adds the trainer content modifier for /app/trainer routes", () => {
    const { container } = render(
      <ClientLayout user={user} path="/app/trainer" onNavigate={vi.fn()} onLogout={vi.fn()}>
        <div>trainer</div>
      </ClientLayout>,
    );

    expect(container.querySelector("main.client-content--trainer")).toBeInTheDocument();
  });

  it("keeps non-trainer routes on the default content class", () => {
    const { container } = render(
      <ClientLayout user={user} path="/app/history" onNavigate={vi.fn()} onLogout={vi.fn()}>
        <div>history</div>
      </ClientLayout>,
    );

    const main = container.querySelector("main.client-content");
    expect(main).toBeInTheDocument();
    expect(main).not.toHaveClass("client-content--trainer");
  });
});
