import type { KeyboardEvent } from "react";

type ComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  loading: boolean;
};

export function Composer({ value, onChange, onSend, disabled, loading }: ComposerProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled && value.trim()) {
        onSend();
      }
    }
  };

  return (
    <div className="composer">
      <textarea
        className="composer__input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Введите сообщение клиенту"
        rows={1}
        disabled={disabled}
      />
      <button type="button" className="composer__send" onClick={onSend} disabled={disabled || !value.trim()}>
        {loading ? "..." : "Отправить"}
      </button>
    </div>
  );
}
