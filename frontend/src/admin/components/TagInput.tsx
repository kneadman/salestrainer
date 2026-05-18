import { useMemo } from "react";

export function TagInput(props: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label: string;
}) {
  const tags = useMemo(() => {
    return props.value
      .split(";")
      .map((t) => t.trim())
      .filter(Boolean);
  }, [props.value]);

  return (
    <label>
      <span>{props.label}</span>
      <input
        type="text"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        placeholder={props.placeholder || "Значение 1; Значение 2; Значение 3"}
      />
      {tags.length > 0 && (
        <div className="tag-chips">
          {tags.map((tag, i) => (
            <span key={i} className="tag-chip">
              {tag}
            </span>
          ))}
        </div>
      )}
    </label>
  );
}
