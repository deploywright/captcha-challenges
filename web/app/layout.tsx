import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CAPTCHA Benchmark - Human vs AI Visual Evaluation",
  description:
    "A standardized visual perception benchmark evaluating human cognitive processing vs. machine vision models across multi-level visual challenges.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0f1117] text-gray-100 antialiased min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
