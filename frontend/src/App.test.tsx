import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { AuthUser } from "./types";

const { MockApiError, getMeMock, logoutMock } = vi.hoisted(() => {
  class MockApiError extends Error {
    status?: number;

    constructor(message: string, status?: number) {
      super(message);
      this.status = status;
    }
  }

  return {
    MockApiError,
    getMeMock: vi.fn(),
    logoutMock: vi.fn(),
  };
});

vi.mock("./api", () => ({
  ApiError: MockApiError,
  getMe: () => getMeMock(),
  logout: () => logoutMock(),
}));

vi.mock("./admin/AdminApp", () => ({
  AdminApp: ({ path }: { path: string }) => <div data-testid="admin-app">{path}</div>,
}));

vi.mock("./client/ClientApp", () => ({
  ClientApp: ({ path }: { path: string }) => <div data-testid="client-app">{path}</div>,
}));

vi.mock("./components/LoginPage", () => ({
  LoginPage: () => <div data-testid="login-page">login</div>,
}));

vi.mock("./components/LandingPage", () => ({
  LandingPage: () => <div data-testid="landing-page">landing</div>,
}));

vi.mock("./demo/DemoPage", () => ({
  DemoPage: () => <div data-testid="demo-page">demo</div>,
}));

const internalAdmin: AuthUser = {
  id: "admin-1",
  email: "admin@example.test",
  role: "internal_admin",
  must_change_password: false,
  client_account: {
    id: "client-1",
    name: "Client",
    slug: "client",
  },
};

describe("App router", () => {
  beforeEach(() => {
    getMeMock.mockReset();
    logoutMock.mockReset();
    sessionStorage.clear();
  });

  it("stores protected route with query string before redirecting unauthenticated users to login", async () => {
    getMeMock.mockRejectedValue(new MockApiError("Unauthorized", 401));

    render(
      <MemoryRouter initialEntries={["/admin/organizations/org-1?tab=users"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("login-page")).toBeInTheDocument();
    expect(sessionStorage.getItem("salestrainer.postLoginRedirect")).toBe("/admin/organizations/org-1?tab=users");
  });

  it("passes direct admin route query string to the admin app", async () => {
    getMeMock.mockResolvedValue({ user: internalAdmin });

    render(
      <MemoryRouter initialEntries={["/admin/organizations/org-1?tab=users"]}>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("admin-app")).toHaveTextContent("/admin/organizations/org-1?tab=users"));
  });
});
