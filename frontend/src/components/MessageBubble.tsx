type MessageBubbleProps = {
  side: "manager" | "client";
  text: string;
};

export function MessageBubble({ side, text }: MessageBubbleProps) {
  return (
    <div className={`message-row message-row--${side}`}>
      <div className={`message-bubble message-bubble--${side}`}>{text}</div>
    </div>
  );
}
