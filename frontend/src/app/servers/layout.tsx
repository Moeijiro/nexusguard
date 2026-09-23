import type { Metadata } from "next";
import { SessionGate } from "@/components/app/session";

export const metadata: Metadata = { title: "Dashboard", robots: { index: false, follow: false } };

export default function ServersLayout({ children }: LayoutProps<"/servers">) {
  return <SessionGate>{children}</SessionGate>;
}
