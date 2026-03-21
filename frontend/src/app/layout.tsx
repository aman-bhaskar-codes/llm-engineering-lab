import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/providers/Providers";

export const metadata: Metadata = {
  title: "Structured Extraction Intelligence Engine",
  description: "ChatGPT-level structured extraction for documents and text."
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

