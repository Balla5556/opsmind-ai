import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = { title: "OpsMind AI | Incident Intelligence", description: "Synthetic AIOps telemetry and incident intelligence MVP." };
export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
