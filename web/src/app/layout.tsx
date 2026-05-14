import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blender AI Director",
  description: "AI-powered 3D scene generation and control via natural language — powered by Gemini + MCP",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ height: "100vh", overflow: "hidden" }}>{children}</body>
    </html>
  );
}
