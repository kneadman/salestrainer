import { render } from "@testing-library/react";
import { ChatWindow } from "./ChatWindow";
import type { TurnPublicDTO } from "../types";

const firstTurn: TurnPublicDTO = {
  turn_index: 1,
  manager_message: "Привет, чем занимаетесь?",
  client_answer: "Веду учет и отчетность.",
  interest_before: 40,
  interest_delta: 3,
  interest_after: 43,
  stage_before: "opening",
  stage_after: "discovery",
  created_at: "2026-05-08T00:00:00Z",
};

const secondTurn: TurnPublicDTO = {
  turn_index: 2,
  manager_message: "Как сейчас устроен процесс?",
  client_answer: "Много ручной работы.",
  interest_before: 43,
  interest_delta: 4,
  interest_after: 47,
  stage_before: "discovery",
  stage_after: "discovery",
  created_at: "2026-05-08T00:01:00Z",
};

describe("ChatWindow", () => {
  const mockScrollIntoView = () => {
    const scrollIntoView = vi.fn();
    Object.defineProperty(window.HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView,
    });
    return scrollIntoView;
  };

  it("scrolls to the bottom when turns change", () => {
    const scrollIntoView = mockScrollIntoView();

    const { rerender } = render(<ChatWindow turns={[firstTurn]} loading={false} publicBrief="Краткий бриф" />);

    expect(scrollIntoView).toHaveBeenCalledTimes(1);

    rerender(<ChatWindow turns={[firstTurn, secondTurn]} loading={false} publicBrief="Краткий бриф" />);

    expect(scrollIntoView).toHaveBeenCalledTimes(2);
    expect(scrollIntoView).toHaveBeenLastCalledWith({ behavior: "smooth", block: "end" });
  });

  it("scrolls to the bottom when loading state changes", () => {
    const scrollIntoView = mockScrollIntoView();

    const { rerender } = render(<ChatWindow turns={[firstTurn]} loading={false} />);

    expect(scrollIntoView).toHaveBeenCalledTimes(1);

    rerender(<ChatWindow turns={[firstTurn]} loading />);

    expect(scrollIntoView).toHaveBeenCalledTimes(2);
    expect(scrollIntoView).toHaveBeenLastCalledWith({ behavior: "smooth", block: "end" });
  });
});
