import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionHeader } from "./SessionHeader";

describe("SessionHeader", () => {
  it("renders the report button next to new session and opens the report", async () => {
    const user = userEvent.setup();
    const onOpenReport = vi.fn();
    const onNewSession = vi.fn();

    const { container } = render(
      <SessionHeader
        busy={false}
        canFinish
        canShowReport
        onNewSession={onNewSession}
        onOpenReport={onOpenReport}
        onFinish={vi.fn()}
        onLogout={vi.fn()}
      />,
    );

    const actions = container.querySelector(".session-header__actions");
    expect(actions).not.toBeNull();
    expect(actions).toContainElement(screen.getByRole("button", { name: "Новая тренировка" }));
    expect(actions).toContainElement(screen.getByRole("button", { name: "Открыть итоговый отчёт" }));

    const buttons = within(actions as HTMLElement).getAllByRole("button");
    expect(buttons[0]).toHaveTextContent("Новая тренировка");
    expect(buttons[1]).toHaveTextContent("Отчёт");

    await user.click(screen.getByRole("button", { name: "Открыть итоговый отчёт" }));

    expect(onOpenReport).toHaveBeenCalledTimes(1);
    expect(onNewSession).not.toHaveBeenCalled();
  });

  it("does not render the report button when report access is unavailable", () => {
    render(
      <SessionHeader
        busy={false}
        canFinish
        canShowReport={false}
        onNewSession={vi.fn()}
        onOpenReport={vi.fn()}
        onFinish={vi.fn()}
        onLogout={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Открыть итоговый отчёт" })).not.toBeInTheDocument();
  });
});
