import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth-provider";
import { ToastProvider } from "@/components/toast";

export const metadata: Metadata = {
  title: "대시보드",
  description: "콘텐츠 + 자동매매 대시보드",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-[#0f0f13] text-gray-200 antialiased">
        <AuthProvider><ToastProvider>{children}</ToastProvider></AuthProvider>
      </body>
    </html>
  );
}
