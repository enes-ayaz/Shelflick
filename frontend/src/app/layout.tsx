import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Shelflick — Kişisel Medya & Akıllı Keşif Asistanı",
  description: "Yapay zeka destekli, kişisel zevkine ve ruh haline göre film, dizi ve anime keşif motoru.",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr" className="dark">
      <body className="bg-[#0a0a0c] text-neutral-100 min-h-screen relative antialiased selection:bg-indigo-600 selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

