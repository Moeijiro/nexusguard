import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const sans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const mono = Geist_Mono({ variable: "--font-mono", subsets: ["latin"] });

const description = "Discord security and moderation: rule-based detection, an auditable action engine, and a real-time dashboard.";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: { default: "NexusGuard — Discord security & moderation", template: "%s · NexusGuard" },
  description,
  openGraph: { title: "NexusGuard", description, type: "website" },
};

export const viewport: Viewport = { themeColor: "#12151b", colorScheme: "dark" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`dark ${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground">
          Skip to content
        </a>
        <TooltipProvider delayDuration={150}>
          {children}
          <Toaster position="bottom-right" richColors closeButton />
        </TooltipProvider>
      </body>
    </html>
  );
}
