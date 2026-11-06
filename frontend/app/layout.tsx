import "./globals.css";
import { Geist, Geist_Mono, Space_Grotesk } from "next/font/google";
import { ServiceWorkerRegister } from "@/components/ServiceWorkerRegister";

const sans = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", display: "swap" });
const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-space", display: "swap" });

export const metadata = {
  manifest: "/manifest.webmanifest",
};

export const viewport = {
  themeColor: "#090d16",
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${sans.variable} ${mono.variable} ${display.variable}`}>
      <body className="min-h-screen antialiased">
        <ServiceWorkerRegister />
        {children}
      </body>
    </html>
  );
}
