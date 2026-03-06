import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "RFP Copilot",
  description: "Bootstrap monorepo for proposal drafting, mapping, and export workflows."
};

type RootLayoutProps = {
  children: React.ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
