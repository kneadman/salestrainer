import { render, screen } from "@testing-library/react";
import { LandingPage } from "./LandingPage";

vi.mock("../api", () => ({
  submitLead: vi.fn(),
}));

describe("LandingPage", () => {
  beforeEach(() => {
    /** Provide browser APIs used by the landing demo in jsdom. */
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    class MockIntersectionObserver {
      /** Keep the demo component mountable without a real viewport observer. */
      observe = vi.fn();
      disconnect = vi.fn();
    }

    Object.defineProperty(window, "IntersectionObserver", {
      configurable: true,
      writable: true,
      value: MockIntersectionObserver,
    });
  });

  it("renders the hero, product demo, and primary CTA", () => {
    render(<LandingPage authenticated={false} />);

    expect(screen.getByRole("heading", { level: 1, name: /Тренируйте сложные разговоры до встречи/i })).toBeInTheDocument();
    expect(screen.getAllByTestId("landing-demo").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /Попробовать демо/i }).length).toBeGreaterThan(0);
  });
  it("renders the shared logo asset", () => {
    const { container } = render(<LandingPage authenticated={false} />);

    expect(container.querySelector('img[src="/logo.svg"]')).toBeInTheDocument();
  });
});
