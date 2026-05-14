"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Square } from "lucide-react";

export default function InputBar({
  onSubmit,
  onStop,
  isDisabled,
}: {
  onSubmit: (text: string) => void;
  onStop?: () => void;
  isDisabled: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!value.trim() || isDisabled) return;
    onSubmit(value.trim());
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  useEffect(() => {
    autoResize();
  }, [value]);

  return (
    <div
      style={{
        borderRadius: "var(--radius-xl)",
        border: `1px solid ${isDisabled ? "var(--border)" : "var(--border-accent)"}`,
        background: "var(--bg-elevated)",
        display: "flex",
        alignItems: "flex-end",
        gap: 8,
        padding: "10px 12px",
        transition: "border-color 0.2s",
        boxShadow: isDisabled ? "none" : "0 0 20px rgba(124,58,237,0.1)",
      }}
    >
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        placeholder="Describe a 3D scene, action, or ask about the current scene..."
        style={{
          flex: 1,
          resize: "none",
          background: "transparent",
          border: "none",
          outline: "none",
          color: "var(--text-primary)",
          fontFamily: "var(--font-sans)",
          fontSize: "0.875rem",
          lineHeight: 1.6,
          overflowY: "hidden",
          opacity: isDisabled ? 0.5 : 1,
        }}
      />

      <div style={{ display: "flex", gap: 6, flexShrink: 0, alignItems: "center" }}>
        <span
          style={{
            fontSize: "0.65rem",
            color: "var(--text-muted)",
            display: value.trim() || isDisabled ? "none" : "block",
          }}
        >
          ⏎ send
        </span>

        {isDisabled ? (
          <button
            onClick={onStop}
            style={{
              width: 34,
              height: 34,
              borderRadius: "50%",
              background: "rgba(244, 63, 94, 0.1)",
              border: "1px solid rgba(244, 63, 94, 0.4)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s",
            }}
            title="Stop Generation"
          >
            <Square size={14} fill="var(--error)" color="var(--error)" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!value.trim() || isDisabled}
            style={{
              width: 34,
              height: 34,
              borderRadius: "50%",
              background: value.trim() && !isDisabled
                ? "linear-gradient(135deg, var(--accent), var(--accent-light))"
                : "var(--bg-card)",
              border: "1px solid var(--border-accent)",
              cursor: value.trim() && !isDisabled ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s",
              opacity: !value.trim() || isDisabled ? 0.4 : 1,
            }}
          >
            <Send size={15} color="white" />
          </button>
        )}
      </div>
    </div>
  );
}
