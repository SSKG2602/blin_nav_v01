import type { Metadata } from "next";
import "./globals.css";
import "../styles/animations.css";

export const metadata: Metadata = {
  title: "BlindNav Demo Shell",
  description: "BlindNav / Luminar operator shell for live demo execution."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
