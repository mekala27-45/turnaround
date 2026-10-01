import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Shell } from "@/components/Shell";
import { THEME_SCRIPT } from "@/components/ThemeToggle";
import palette from "@/theme/palette.json";

import { courier, franklin, spectral } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "turnaround: why your flight is late", template: "%s | turnaround" },
  description:
    "A data story in eight chapters on every scheduled US domestic flight since January 2015: what on time means, how much delay was inherited from the previous flight, the fair carrier ranking, the meltdowns, and the connection buffer that keeps a misconnect under ten percent.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: palette.light.surface },
    { media: "(prefers-color-scheme: dark)", color: palette.dark.surface },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // The theme script sets data-theme before first paint, so the server markup cannot match it.
    <html lang="en" suppressHydrationWarning className={`${franklin.variable} ${spectral.variable} ${courier.variable}`}>
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
