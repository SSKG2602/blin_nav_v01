import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BlindNav Foundation",
  description: "BlindNav / Luminar repository foundation bootstrap."
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
