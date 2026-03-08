import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Luminar Voice Shopping Assistant",
  description: "Voice-first AI shopping assistant frontend for Luminar."
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
