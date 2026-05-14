"use client";

import { useState, useRef, useEffect, useCallback } from "react";

export type LogEntry = {
  id: string;
  raw: string;
  type: "scene" | "tool_call" | "tool_result" | "reasoning" | "error" | "connecting" | "generic";
  toolName?: string;
  timestamp: number;
};

export type Message = {
  id: string;
  role: "user" | "agent";
  content: string;
};

export type SceneObject = {
  name: string;
  type: string;
};

export function useAgentStream() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [images, setImages] = useState<string[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [activeSkills, setActiveSkills] = useState<string[]>([]);
  const [sceneObjects, setSceneObjects] = useState<SceneObject[]>([]);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const classifyLog = (msg: string): Omit<LogEntry, "id" | "timestamp" | "raw"> => {
    const m = msg.toLowerCase();
    if (m.includes("connecting") || m.includes("connect"))
      return { type: "connecting" };
    if (m.includes("fetching scene") || m.includes("scene state"))
      return { type: "scene" };
    if (m.includes("executing tool:")) {
      const match = msg.match(/Executing tool:\s*(.+)/i);
      return { type: "tool_call", toolName: match?.[1]?.trim() };
    }
    if (m.includes("finished executing:")) {
      const match = msg.match(/Finished executing:\s*(.+)/i);
      return { type: "tool_result", toolName: match?.[1]?.trim() };
    }
    if (m.includes("agent reasoning:") || m.includes("reasoning loop"))
      return { type: "reasoning" };
    if (m.includes("❌") || m.includes("error") || m.includes("fatal"))
      return { type: "error" };
    return { type: "generic" };
  };

  const addLog = useCallback((raw: string) => {
    const classified = classifyLog(raw);
    setLogs((prev) => [
      ...prev,
      { id: Math.random().toString(36).slice(2), raw, timestamp: Date.now(), ...classified },
    ]);
  }, []);

  const sendPrompt = useCallback(async (prompt: string) => {
    if (!prompt.trim() || isThinking) return;

    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: "user", content: prompt },
    ]);
    setLogs([]);
    setActiveSkills([]);
    setIsThinking(true);

    try {
      const res = await fetch("http://localhost:3005/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!res.body) throw new Error("No SSE stream");

      const reader = res.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          if (!chunk.trim()) continue;
          const eventMatch = chunk.match(/event:\s*([a-z]+)/);
          const dataMatch  = chunk.match(/data:\s*(.*)/);
          if (!eventMatch || !dataMatch) continue;

          const eventType = eventMatch[1];
          try {
            const data = JSON.parse(dataMatch[1]);
            if (eventType === "log") {
              addLog(data as string);
            } else if (eventType === "skills") {
              setActiveSkills(data as string[]);
            } else if (eventType === "image") {
              setImages((prev) => [...prev, `http://localhost:3005${data}`]);
            } else if (eventType === "done") {
              setMessages((prev) => [
                ...prev,
                { id: Date.now().toString(), role: "agent", content: data as string },
              ]);
              setIsThinking(false);
            }
          } catch {/* ignore parse err */}
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addLog(`❌ Connection error: ${msg}`);
      setIsThinking(false);
    }
  }, [isThinking, addLog]);

  const stopPrompt = useCallback(() => {
    if (readerRef.current) {
      readerRef.current.cancel("User cancelled");
      readerRef.current = null;
    }
    setIsThinking(false);
    addLog("🛑 Agent paused by user.");
  }, [addLog]);

  return { messages, logs, images, isThinking, activeSkills, sceneObjects, sendPrompt, stopPrompt };
}
