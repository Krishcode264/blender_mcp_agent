"use client";

import { CheckCircle, Clock, Box, Layers } from "lucide-react";
import type { LogEntry } from "../hooks/useAgentStream";

function timeAgo(ts: number) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s ago`;
  return `${Math.floor(s / 60)}m ago`;
}

export default function TaskTracker({ logs }: { logs: LogEntry[] }) {
  const toolCalls = logs.filter((l) => l.type === "tool_call");
  const toolResults = logs.filter((l) => l.type === "tool_result");
  const resultNames = new Set(toolResults.map((r) => r.toolName));

  if (toolCalls.length === 0)
    return (
      <div
        style={{
          padding: "16px",
          color: "var(--text-muted)",
          fontSize: "0.75rem",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
        }}
      >
        <Layers size={22} style={{ opacity: 0.25 }} />
        <span>No tasks yet</span>
      </div>
    );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {toolCalls.map((call) => {
        const done = resultNames.has(call.toolName);
        return (
          <div
            key={call.id}
            className="fade-in"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 10px",
              borderRadius: "var(--radius-sm)",
              background: done ? "var(--success-bg)" : "var(--bg-card)",
              border: `1px solid ${done ? "rgba(34,197,94,0.2)" : "var(--border)"}`,
              transition: "all 0.3s",
            }}
          >
            {done ? (
              <CheckCircle size={13} color="var(--success)" />
            ) : (
              <Clock size={13} color="var(--text-muted)" className="spin" />
            )}
            <span
              style={{
                flex: 1,
                fontSize: "0.72rem",
                color: done ? "var(--success)" : "var(--text-secondary)",
                fontFamily: "var(--font-mono)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {call.toolName || "tool"}
            </span>
            <span style={{ fontSize: "0.62rem", color: "var(--text-muted)", flexShrink: 0 }}>
              {timeAgo(call.timestamp)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
