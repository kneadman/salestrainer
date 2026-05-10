import { render, screen } from "@testing-library/react";
import { LandingPage } from "./LandingPage";

vi.mock("../api", () => ({
  submitLead: vi.fn(),
}));

describe("LandingPage", () => {
  it("renders the hero heading and primary CTA", () => {
    render(<LandingPage authenticated={false} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /Тренируйте сложные разговоры до встречи/i,
      })
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: /Попробовать демо/i }).length
    ).toBeGreaterThan(0);
  });

  it("renders the brand logo mark", () => {
    const { container } = render(<LandingPage authenticated={false} />);

    expect(container.querySelector(".gradient-accent")).toBeInTheDocument();
  });
});
