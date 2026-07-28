import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LandingPage } from "./LandingPage";

const submitLeadMock = vi.fn();

vi.mock("../api", () => ({
  submitLead: (payload: unknown) => submitLeadMock(payload),
  listBlogPostsPublic: vi.fn().mockResolvedValue({ items: [] }),
}));

describe("LandingPage", () => {
  beforeEach(() => {
    submitLeadMock.mockReset();
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });
    class MockIntersectionObserver {
      observe = vi.fn();
      disconnect = vi.fn();
    }
    Object.defineProperty(window, "IntersectionObserver", {
      configurable: true,
      writable: true,
      value: MockIntersectionObserver,
    });
  });

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

  it("renders lead form fields and legal links", () => {
    render(<LandingPage authenticated={false} />);

    expect(screen.getByPlaceholderText(/Имя/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Email/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Телефон/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Компания/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /обработку персональных данных/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Политика конфиденциальности/i })
    ).toBeInTheDocument();
  });

  it("shows validation error when submitting without consent", async () => {
    render(<LandingPage authenticated={false} />);

    const form = screen.getByPlaceholderText(/Имя/i).closest("form")!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(
        screen.getByText(/Проверьте форму и согласие/i)
      ).toBeInTheDocument();
    });
  });

  it("submits the form successfully when consent is given", async () => {
    submitLeadMock.mockResolvedValueOnce(undefined);
    render(<LandingPage authenticated={false} />);

    fireEvent.change(screen.getByPlaceholderText(/Имя/i), {
      target: { value: "Иван" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Email/i), {
      target: { value: "ivan@test.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Телефон/i), {
      target: { value: "+79990000000" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Компания/i), {
      target: { value: "ООО Тест" },
    });

    const roleSelect = screen.getByDisplayValue(/Выберите роль/i);
    fireEvent.change(roleSelect, { target: { value: "rop" } });

    const sizeSelect = screen.getByDisplayValue(/Выберите диапазон/i);
    fireEvent.change(sizeSelect, { target: { value: "6-20" } });

    const consentCheckbox = screen.getByRole("checkbox", {
      name: /Согласен на/i,
    });
    fireEvent.click(consentCheckbox);

    const form = screen.getByPlaceholderText(/Имя/i).closest("form")!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(
        screen.getByText(/Заявка отправлена/i)
      ).toBeInTheDocument();
    });

    expect(submitLeadMock).toHaveBeenCalledTimes(1);
    const payload = submitLeadMock.mock.calls[0][0];
    expect(payload.name).toBe("Иван");
    expect(payload.email).toBe("ivan@test.com");
    expect(payload.consent_personal_data).toBe(true);
  });

  it("renders footer with dynamic year and cookie link", () => {
    render(<LandingPage authenticated={false} />);

    const year = new Date().getFullYear();
    expect(screen.getByText(new RegExp(`© ${year} Replikor`))).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Cookie/i })
    ).toBeInTheDocument();
  });
});
