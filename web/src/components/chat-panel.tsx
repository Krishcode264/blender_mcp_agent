"use client";

import { useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Clapperboard, User, Bot, Loader2 } from "lucide-react";
import type { Message } from "../hooks/useAgentStream";

export default function ChatPanel({
  messages,
  isThinking,
}: {
  messages: Message[];
  isThinking: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  return (
    <div
      className="custom-scrollbar"
      style={{
        flex: 1,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        padding: "8px 0 4px",
      }}
    >
      {messages.length === 0 ? (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "16px",
            color: "var(--text-muted)",
            textAlign: "center",
            padding: "48px 24px",
          }}
        >
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: "50%",
              background: "var(--accent-glow)",
              border: "1px solid var(--border-accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            className="pulse-glow"
          >
            <Clapperboard size={28} color="var(--accent-light)" />
          </div>
          <div>
            <p style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
              Blender AI Director
            </p>
            <p style={{ fontSize: "0.8rem", lineHeight: 1.6 }}>
              Describe a scene, animation, or 3D action
              <br />
              and watch the AI build it in Blender.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
            {[
              "Add a glowing cube in the center",
              "Create a sunset scene with 3 lights",
              "What objects are in the scene?",
              "Render the current view",
            ].map((hint) => (
              <span
                key={hint}
                style={{
                  fontSize: "0.72rem",
                  padding: "4px 10px",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 99,
                  color: "var(--text-muted)",
                  cursor: "default",
                }}
              >
                {hint}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <>
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="fade-in"
              style={{
                display: "flex",
                gap: "10px",
                alignItems: "flex-start",
                flexDirection: msg.role === "user" ? "row-reverse" : "row",
              }}
            >
              {/* Avatar */}
              <div
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: msg.role === "user" ? "var(--accent-glow)" : "rgba(6,182,212,0.12)",
                  border: `1px solid ${msg.role === "user" ? "var(--border-accent)" : "rgba(6,182,212,0.25)"}`,
                }}
              >
                {msg.role === "user" ? (
                  <User size={14} color="var(--accent-light)" />
                ) : (
                  <Bot size={14} color="var(--accent-2)" />
                )}
              </div>

              {/* Bubble */}
              <div
                style={{
                  maxWidth: "82%",
                  padding: "10px 14px",
                  borderRadius: msg.role === "user" ? "14px 4px 14px 14px" : "4px 14px 14px 14px",
                  background: msg.role === "user"
                    ? "linear-gradient(135deg, rgba(124,58,237,0.22), rgba(168,85,247,0.15))"
                    : "var(--bg-card)",
                  border: `1px solid ${msg.role === "user" ? "var(--border-accent)" : "var(--border)"}`,
                  fontSize: "0.875rem",
                  lineHeight: 1.6,
                }}
              >
                {msg.role === "agent" ? (
                  <div className="prose">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <span style={{ color: "var(--text-primary)" }}>{msg.content}</span>
                )}
              </div>
            </div>
          ))}

          {/* Thinking indicator */}
          {isThinking && (
            <div className="fade-in" style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <div
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "rgba(6,182,212,0.12)",
                  border: "1px solid rgba(6,182,212,0.25)",
                }}
              >
                <Bot size={14} color="var(--accent-2)" />
              </div>
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "4px 14px 14px 14px",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <Loader2 size={14} color="var(--accent-light)" className="spin" />
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  Thinking<span className="cursor-blink">▋</span>
                </span>
              </div>
            </div>
          )}
        </>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
