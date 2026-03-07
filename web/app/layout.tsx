import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "RFP Copilot",
  description: "Bootstrap monorepo for proposal drafting and in-editor download workflows."
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
