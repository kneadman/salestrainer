import { useEffect, useRef } from "react";
import type { TurnPublicDTO } from "../types";
import { MessageBubble } from "./MessageBubble";

type ChatWindowProps = {
  turns: TurnPublicDTO[];
  loading: boolean;
  publicBrief?: string;
};

export function ChatWindow({ turns, loading, publicBrief }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, loading]);

  return (
    <div className="chat-window">
      {publicBrief ? <div className="chat-brief">{publicBrief}</div> : null}

      {turns.length === 0 ? (
        <div className="chat-empty">
          Спросите про роль, текущий процесс, боли и критерии, прежде чем вести к следующему шагу.
        </div>
      ) : null}

      {turns.map((turn) => (
        <div key={turn.turn_index} className="chat-turn">
          <MessageBubble side="manager" text={turn.manager_message} />
          <MessageBubble side="client" text={turn.client_answer} />
        </div>
      ))}

      {loading ? (
        <div className="chat-turn">
          <MessageBubble side="client" text="Клиент печатает..." />
        </div>
      ) : null}

      <div ref={bottomRef} />
    </div>
  );
}
