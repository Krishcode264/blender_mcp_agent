"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import {
  Brain,
  Wrench,
  CheckCircle,
  XCircle,
  Search,
  Wifi,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  Zap,
  BookOpen,
  Copy,
  CopyCheck,
  ClipboardList,
} from "lucide-react";
import type { LogEntry } from "../hooks/useAgentStream";

const TOOL_ICONS: Record<string, string> = {
  get_scene_info: "🔍",
  get_object_info: "🔎",
  take_screenshot: "📸",
  execute_blender_code: "⚙️",
  render_scene: "🎬",
  reply_to_user: "💬",
  request_toolset: "📦",
  set_keyframe: "🎞",
  set_object_color: "🎨",
  move_object: "📐",
  create_object: "➕",
  create_empty: "🔘",
  delete_object: "🗑",
  scale_object: "📏",
  rotate_object: "🔄",
  parent_object: "🔗",
  add_cycle_modifier: "♾️",
  set_interpolation: "〰️",
  set_material_properties: "✨",
  set_split_material: "🎭",
  add_modifier: "🔩",
  add_circular_orbit: "🌀",
};

function stripPrefix(raw: string): string {
  return raw
    .replace(/^(Executing tool:|Agent reasoning:|Fetching scene.*?|Finished executing:|❌ Tool error from Blender:|Agent Message:|Agent finished:)/i, "")
    .trim();
}

/** Small copy button with a ✓ flash on success */
function CopyBtn({ text, size = 11 }: { text: string; size?: number }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <button
      onClick={handleCopy}
      title={copied ? "Copied!" : "Copy"}
      style={{
        background: "none",
        border: "none",
        cursor: "pointer",
        padding: "2px 4px",
        borderRadius: 3,
        color: copied ? "var(--success)" : "var(--text-muted)",
        display: "flex",
        alignItems: "center",
        flexShrink: 0,
        opacity: 0.7,
        transition: "opacity 0.15s, color 0.15s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
      onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.7")}
    >
      {copied
        ? <CopyCheck size={size} />
        : <Copy size={size} />}
    </button>
  );
}

function LogCard({
  entry,
  index,
  isLast,
}: {
  entry: LogEntry;
  index: number;
  isLast: boolean;
}) {
  // Errors always start expanded; last card auto-expands; rest collapsed
  const [expanded, setExpanded] = useState(entry.type === "error" || isLast);

  useEffect(() => {
    if (!isLast && entry.type !== "error") setExpanded(false);
  }, [isLast, entry.type]);

  const meta: Record<string, { border: string; bg: string; label: string; labelColor: string }> = {
    tool_call:   { border: "rgba(99,102,241,0.35)",  bg: "rgba(99,102,241,0.07)",  label: "tool",    labelColor: "var(--accent-light)" },
    tool_result: { border: "rgba(34,197,94,0.25)",   bg: "rgba(34,197,94,0.06)",   label: "done",    labelColor: "var(--success)" },
    reasoning:   { border: "rgba(245,158,11,0.25)",  bg: "rgba(245,158,11,0.06)",  label: "think",   labelColor: "#f59e0b" },
    error:       { border: "rgba(244,63,94,0.45)",   bg: "rgba(244,63,94,0.10)",   label: "error",   labelColor: "var(--error)" },
    scene:       { border: "rgba(56,189,248,0.25)",  bg: "rgba(56,189,248,0.06)",  label: "scene",   labelColor: "var(--info)" },
    recipe:      { border: "rgba(168,85,247,0.30)",  bg: "rgba(168,85,247,0.07)",  label: "recipe",  labelColor: "#a855f7" },
    connecting:  { border: "var(--border)",          bg: "transparent",            label: "info",    labelColor: "var(--text-muted)" },
  };
  const m = meta[entry.type] ?? meta.connecting;

  const getIcon = () => {
    switch (entry.type) {
      case "scene":       return <Search size={11} color="var(--info)" />;
      case "tool_call":   return <Wrench size={11} color="var(--accent-light)" />;
      case "tool_result": return <CheckCircle size={11} color="var(--success)" />;
      case "reasoning":   return <Brain size={11} color="#f59e0b" />;
      case "error":       return <XCircle size={11} color="var(--error)" />;
      case "recipe":      return <BookOpen size={11} color="#a855f7" />;
      case "connecting":  return <Wifi size={11} color="var(--text-muted)" />;
      default:            return <Zap size={11} color="var(--text-muted)" />;
    }
  };

  // Every card is expandable if it has meaningful content
  const isExpandable = entry.raw.length > 35;

  const shortText = stripPrefix(entry.raw);
  const displayText =
    entry.type === "tool_call"
      ? `${TOOL_ICONS[entry.toolName || ""] || "🔧"} ${entry.toolName}`
      : shortText;

  return (
    <div
      className="fade-in"
      style={{
        borderRadius: 6,
        border: `1px solid ${m.border}`,
        background: m.bg,
        overflow: "hidden",
        flexShrink: 0,
        animationDelay: `${Math.min(index, 10) * 20}ms`,
      }}
    >
      {/* ── Single-row header ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "5px 8px",
          cursor: isExpandable ? "pointer" : "default",
          userSelect: "none",
          minHeight: 28,
        }}
        onClick={() => isExpandable && setExpanded((e) => !e)}
      >
        {/* step number */}
        <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums", flexShrink: 0, minWidth: 18, textAlign: "right" }}>
          {index + 1}
        </span>

        {/* type icon */}
        <span style={{ flexShrink: 0 }}>{getIcon()}</span>

        {/* label pill */}
        <span
          style={{
            fontSize: "0.58rem",
            fontWeight: 600,
            color: m.labelColor,
            background: `${m.labelColor}18`,
            border: `1px solid ${m.labelColor}30`,
            borderRadius: 3,
            padding: "1px 5px",
            flexShrink: 0,
            letterSpacing: "0.03em",
            textTransform: "uppercase",
          }}
        >
          {m.label}
        </span>

        {/* main text */}
        <span
          style={{
            fontSize: "0.7rem",
            color: entry.type === "error" ? "var(--error)" : entry.type === "tool_call" ? "var(--accent-light)" : "var(--text-secondary)",
            flex: 1,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            fontFamily: entry.type === "reasoning" ? "inherit" : "var(--font-mono)",
            fontWeight: entry.type === "tool_call" || entry.type === "error" ? 500 : 400,
          }}
        >
          {displayText || entry.raw}
        </span>

        {/* copy this card */}
        <CopyBtn text={entry.raw} size={11} />

        {/* expand chevron */}
        {isExpandable && (
          <span style={{ color: "var(--text-muted)", flexShrink: 0 }}>
            {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          </span>
        )}
      </div>

      {/* ── Expandable full content ── */}
      {isExpandable && expanded && (
        <div
          className="custom-scrollbar"
          style={{
            padding: "4px 8px 8px 32px",
            fontSize: "0.68rem",
            color: entry.type === "error" ? "rgba(248,113,113,0.9)" : "var(--text-muted)",
            lineHeight: 1.6,
            borderTop: `1px solid ${m.border}`,
            maxHeight: 240,
            overflowY: "auto",
            wordBreak: "break-word",
            whiteSpace: "pre-wrap",
            fontFamily: "var(--font-mono)",
          }}
        >
          {entry.raw}
        </div>
      )}
    </div>
  );
}

export default function BrainPanel({
  logs,
  isThinking,
  activeSkills = [],
}: {
  logs: LogEntry[];
  isThinking: boolean;
  activeSkills?: string[];
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [allCopied, setAllCopied] = useState(false);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const copyAll = useCallback(() => {
    if (logs.length === 0) return;
    const text = logs
      .map((e, i) => `[${i + 1}] ${e.type.toUpperCase()}: ${e.raw}`)
      .join("\n\n");
    navigator.clipboard.writeText(text).then(() => {
      setAllCopied(true);
      setTimeout(() => setAllCopied(false), 2000);
    });
  }, [logs]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>

      {/* ── Header ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 14px 8px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 26, height: 26, borderRadius: "50%",
            background: "var(--accent-glow)", border: "1px solid var(--border-accent)",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}
          className={isThinking ? "pulse-glow" : ""}
        >
          <Brain size={13} color="var(--accent-light)" />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1 }}>
            Agent Brain
          </p>
          <p style={{ fontSize: "0.62rem", color: "var(--text-muted)", marginTop: 2 }}>
            {isThinking ? "Processing…" : logs.length > 0 ? `${logs.length} step${logs.length !== 1 ? "s" : ""}` : "Idle"}
          </p>
        </div>

        {/* Copy All button */}
        {logs.length > 0 && (
          <button
            onClick={copyAll}
            title="Copy all log entries"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              background: allCopied ? "rgba(34,197,94,0.12)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${allCopied ? "rgba(34,197,94,0.3)" : "var(--border)"}`,
              borderRadius: 5,
              padding: "3px 8px",
              cursor: "pointer",
              color: allCopied ? "var(--success)" : "var(--text-muted)",
              fontSize: "0.62rem",
              fontWeight: 500,
              flexShrink: 0,
              transition: "all 0.2s",
            }}
          >
            {allCopied ? <CopyCheck size={11} /> : <ClipboardList size={11} />}
            <span>{allCopied ? "Copied!" : "Copy all"}</span>
          </button>
        )}

        {isThinking && (
          <span
            className="badge badge-tool"
            style={{ fontSize: "0.6rem", animation: "pulse-glow 1.8s ease-in-out infinite", flexShrink: 0 }}
          >
            ● Live
          </span>
        )}
      </div>

      {/* ── Active Skills (Cognitive Context) ── */}
      {activeSkills.length > 0 && (
        <div
          style={{
            padding: "8px 14px",
            background: "var(--bg-surface-alt)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <Zap size={10} color="var(--accent-light)" />
            <span style={{ fontSize: "0.6rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Active Skills
            </span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {activeSkills.map((skill) => (
              <span
                key={skill}
                className="fade-in"
                style={{
                  fontSize: "0.58rem",
                  fontWeight: 500,
                  color: "var(--accent-light)",
                  background: "var(--accent-glow)",
                  border: "1px solid var(--border-accent)",
                  borderRadius: 12,
                  padding: "1px 8px",
                  whiteSpace: "nowrap",
                }}
              >
                {skill.replace("_SKILL", "").replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Scrollable log area ── */}
      <div
        ref={containerRef}
        className="custom-scrollbar"
        style={{
          flex: 1, overflowY: "auto", overflowX: "hidden",
          minHeight: 0, padding: "12px 12px",
          display: "flex", flexDirection: "column", gap: 8,
        }}
      >
        {logs.length === 0 && !isThinking && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", gap: 8, fontSize: "0.74rem", textAlign: "center", padding: "32px 16px" }}>
            <MessageSquare size={24} style={{ opacity: 0.18 }} />
            <p style={{ lineHeight: 1.5 }}>Agent steps will appear here<br />as the AI works through your request.</p>
          </div>
        )}

        {logs.map((entry, i) => (
          <LogCard key={entry.id} entry={entry} index={i} isLast={i === logs.length - 1} />
        ))}

        {isThinking && (
          <div className="fade-in shimmer" style={{ borderRadius: 6, border: "1px solid var(--border-accent)", height: 28, flexShrink: 0 }} />
        )}

        <div ref={bottomRef} style={{ height: 1 }} />
      </div>
    </div>
  );
}

