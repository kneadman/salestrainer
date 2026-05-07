import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Composer } from "./Composer";

const voiceRecorderMock = vi.hoisted(() => ({
  useVoiceRecorder: vi.fn(),
}));

vi.mock("../hooks/useVoiceRecorder", () => voiceRecorderMock);

describe("Composer", () => {
  beforeEach(() => {
    voiceRecorderMock.useVoiceRecorder.mockReturnValue({
      state: "idle",
      elapsedSeconds: 0,
      isSupported: true,
      error: null,
      startRecording: vi.fn(),
      stopRecording: vi.fn(),
      toggleRecording: vi.fn(),
      clearError: vi.fn(),
    });
  });

  it("renders textarea and accessible voice/send buttons", () => {
    render(
      <Composer
        value=""
        onChange={vi.fn()}
        onSend={vi.fn()}
        disabled={false}
        loading={false}
        onTranscribeAudio={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    const textarea = screen.getByPlaceholderText("Введите сообщение клиенту");
    const voiceButton = screen.getByRole("button", { name: "Голосовой ввод" });
    const sendButton = screen.getByRole("button", { name: "Отправить" });

    expect(textarea).toHaveAttribute("rows", "1");
    expect(textarea).toHaveClass("composer__input");
    expect(voiceButton).toBeEnabled();
    expect(voiceButton.querySelector("svg")).not.toBeNull();
    expect(sendButton).toBeInTheDocument();
  });

  it("disables the microphone button when voice input is disabled", () => {
    render(
      <Composer
        value=""
        onChange={vi.fn()}
        onSend={vi.fn()}
        disabled={false}
        loading={false}
        onTranscribeAudio={vi.fn().mockResolvedValue(undefined)}
        voiceDisabled
      />,
    );

    expect(screen.getByRole("button", { name: "Голосовой ввод" })).toBeDisabled();
  });

  it("calls onChange when textarea text changes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <Composer
        value=""
        onChange={onChange}
        onSend={vi.fn()}
        disabled={false}
        loading={false}
        onTranscribeAudio={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    await user.type(screen.getByPlaceholderText("Введите сообщение клиенту"), "Привет");

    expect(onChange).toHaveBeenCalled();
  });

  it("sends on Enter without Shift when value is not empty", () => {
    const onSend = vi.fn();

    render(
      <Composer
        value="Привет"
        onChange={vi.fn()}
        onSend={onSend}
        disabled={false}
        loading={false}
        onTranscribeAudio={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    fireEvent.keyDown(screen.getByPlaceholderText("Введите сообщение клиенту"), {
      key: "Enter",
      code: "Enter",
    });

    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("does not send on Shift+Enter", () => {
    const onSend = vi.fn();

    render(
      <Composer
        value="Привет"
        onChange={vi.fn()}
        onSend={onSend}
        disabled={false}
        loading={false}
        onTranscribeAudio={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    fireEvent.keyDown(screen.getByPlaceholderText("Введите сообщение клиенту"), {
      key: "Enter",
      code: "Enter",
      shiftKey: true,
    });

    expect(onSend).not.toHaveBeenCalled();
  });
});
