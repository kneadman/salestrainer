import { render, screen } from "@testing-library/react";
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

  it("renders an accessible microphone button with an icon", () => {
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

    const voiceButton = screen.getByRole("button", { name: "Голосовой ввод" });
    expect(voiceButton).toBeEnabled();
    expect(voiceButton.querySelector("svg")).not.toBeNull();
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
});
