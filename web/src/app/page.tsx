"use client";

import { useState } from "react";
import { useAgentStream } from "../hooks/useAgentStream";
import ChatPanel from "../components/chat-panel";
import BrainPanel from "../components/brain-panel";
import InputBar from "../components/input-bar";
import TaskTracker from "../components/task-tracker";
import RenderPreview from "../components/render-preview";
import {
  Box,
  Layers,
  Settings,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  Circle,
} from "lucide-react";

import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

function SidebarSection({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div
      style={{
        borderBottom: "1px solid var(--border)",
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 14px",
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--text-secondary)",
        }}
      >
        {icon}
        <span style={{ fontSize: "0.72rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", flex: 1, textAlign: "left" }}>
          {title}
        </span>
        {open ? <ChevronLeft size={12} style={{ opacity: 0.5 }} /> : <ChevronRight size={12} style={{ opacity: 0.5 }} />}
      </button>
      {open && <div style={{ padding: "0 10px 12px" }}>{children}</div>}
    </div>
  );
}

function ResizeHandle() {
  return (
    <PanelResizeHandle
      style={{
        width: "2px",
        background: "var(--border)",
        cursor: "col-resize",
        transition: "background 0.2s",
      }}
      onMouseOver={(e) => ((e.target as HTMLElement).style.background = "var(--border-accent)")}
      onMouseOut={(e) => ((e.target as HTMLElement).style.background = "var(--border)")}
    />
  );
}

export default function Home() {
  const { messages, logs, images, isThinking, activeSkills, sendPrompt, stopPrompt } = useAgentStream();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Parse scene objects from logs
  const sceneLog = logs.find((l) => l.type === "scene");

  return (
    <PanelGroup
      direction="horizontal"
      style={{
        height: "100vh",
        overflow: "hidden",
        background: "var(--bg-base)",
      }}
    >
      {/* ── LEFT SIDEBAR ─────────────────────────────────── */}
      <Panel
        defaultSize={20}
        minSize={10}
        maxSize={35}
        collapsible
        collapsedSize={4}
        onCollapse={() => setSidebarCollapsed(true)}
        onExpand={() => setSidebarCollapsed(false)}
        style={{
          background: "var(--bg-surface)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Sidebar header */}
        <div
          style={{
            padding: "14px 12px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: 6,
              background: "linear-gradient(135deg, var(--accent), var(--accent-light))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Clapperboard size={13} color="white" />
          </div>
          {!sidebarCollapsed && (
            <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-primary)", whiteSpace: "nowrap" }}>
              Blender Director
            </span>
          )}
          <button
            onClick={() => {
              // Toggle is handled by react-resizable-panels drag/collapse
            }}
            style={{
              marginLeft: "auto",
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              display: "flex",
              flexShrink: 0,
            }}
          >
            {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>

        {!sidebarCollapsed && (
          <div style={{ flex: 1, overflowY: "auto" }} className="custom-scrollbar">
            {/* Render Preview */}
            <SidebarSection title="Render Preview" icon={<Box size={12} />}>
              <RenderPreview images={images} />
            </SidebarSection>

            {/* Task Tracker */}
            <SidebarSection title="Task Log" icon={<Layers size={12} />}>
              <TaskTracker logs={logs} />
            </SidebarSection>

            {/* Status */}
            <SidebarSection title="Status" icon={<Settings size={12} />}>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {[
                  { label: "Agent Backend", port: 3005 },
                  { label: "Blender MCP", port: 9877 },
                ].map(({ label, port }) => (
                  <div key={port} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.7rem" }}>
                    <Circle
                      size={6}
                      color="var(--success)"
                      fill="var(--success)"
                      style={{ flexShrink: 0 }}
                    />
                    <span style={{ color: "var(--text-secondary)", flex: 1 }}>{label}</span>
                    <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>:{port}</span>
                  </div>
                ))}
              </div>
            </SidebarSection>
          </div>
        )}
      </Panel>

      <ResizeHandle />

      {/* ── CENTER: CHAT ──────────────────────────────────── */}
      <Panel
        defaultSize={55}
        minSize={30}
        style={{
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
        }}
      >
        {/* Top bar */}
        <div
          style={{
            padding: "12px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            gap: 10,
            flexShrink: 0,
          }}
        >
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
            Chat
          </span>
          {isThinking && (
            <span className="badge badge-tool" style={{ marginLeft: 4 }}>
              ● Thinking
            </span>
          )}
          <span style={{ marginLeft: "auto", fontSize: "0.7rem", color: "var(--text-muted)" }}>
            {messages.length} messages
          </span>
        </div>

        {/* Chat messages */}
        <div style={{ flex: 1, overflowY: "hidden", display: "flex", flexDirection: "column", padding: "12px 20px 0" }}>
          <ChatPanel messages={messages} isThinking={isThinking} />
        </div>

        {/* Input */}
        <div style={{ padding: "12px 20px 16px", flexShrink: 0 }}>
          <InputBar onSubmit={sendPrompt} onStop={stopPrompt} isDisabled={isThinking} />
          <p style={{ fontSize: "0.65rem", color: "var(--text-muted)", textAlign: "center", marginTop: 6 }}>
            ↵ Enter to send · Shift+Enter for new line
          </p>
        </div>
      </Panel>

      <ResizeHandle />

      {/* ── RIGHT: BRAIN PANEL ───────────────────────────── */}
      <Panel
        defaultSize={25}
        minSize={15}
        maxSize={50}
        style={{
          background: "var(--bg-surface)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <BrainPanel logs={logs} isThinking={isThinking} activeSkills={activeSkills} />
      </Panel>
    </PanelGroup>
  );
}

