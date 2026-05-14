"use client";

import { useState } from "react";
import { ImageIcon, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";

export default function RenderPreview({ images }: { images: string[] }) {
  const [idx, setIdx] = useState(0);
  const current = images[idx];

  return (
    <div
      style={{
        width: "100%",
        aspectRatio: "16/9",
        borderRadius: "var(--radius-md)",
        background: "var(--bg-base)",
        border: "1px solid var(--border)",
        overflow: "hidden",
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {current ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={current}
            alt={`Blender render ${idx + 1}`}
            className="fade-in"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              display: "block",
            }}
          />

          {/* Controls overlay */}
          {images.length > 1 && (
            <div
              style={{
                position: "absolute",
                bottom: 8,
                left: "50%",
                transform: "translateX(-50%)",
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: "rgba(0,0,0,0.7)",
                backdropFilter: "blur(8px)",
                border: "1px solid var(--border)",
                borderRadius: 99,
                padding: "4px 10px",
              }}
            >
              <button
                onClick={() => setIdx((i) => Math.max(0, i - 1))}
                disabled={idx === 0}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", display: "flex", padding: 2 }}
              >
                <ChevronLeft size={14} />
              </button>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                {idx + 1} / {images.length}
              </span>
              <button
                onClick={() => setIdx((i) => Math.min(images.length - 1, i + 1))}
                disabled={idx === images.length - 1}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", display: "flex", padding: 2 }}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}

          {/* Open link */}
          <a
            href={current}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              position: "absolute",
              top: 8,
              right: 8,
              background: "rgba(0,0,0,0.6)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              padding: "3px 6px",
              display: "flex",
              alignItems: "center",
              gap: 4,
              fontSize: "0.65rem",
              color: "var(--text-muted)",
              textDecoration: "none",
            }}
          >
            <ExternalLink size={10} /> open
          </a>
        </>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 8,
            color: "var(--text-muted)",
          }}
        >
          <ImageIcon size={28} style={{ opacity: 0.15 }} />
          <span style={{ fontSize: "0.7rem" }}>Awaiting render</span>
        </div>
      )}
    </div>
  );
}
