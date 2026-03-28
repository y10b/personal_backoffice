"use client";

import { signIn } from "next-auth/react";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-[#1a1a24] border border-[#2a2a3a] rounded-2xl p-10 text-center max-w-sm w-full">
        <h1 className="text-2xl font-bold text-white mb-2">대시보드</h1>
        <p className="text-gray-500 text-sm mb-8">콘텐츠 + 자동매매</p>
        <button
          onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
          className="w-full bg-white text-gray-800 font-semibold py-3 px-6 rounded-lg hover:bg-gray-100 transition"
        >
          Google 계정으로 로그인
        </button>
        <p className="text-gray-600 text-xs mt-4">허용된 계정만 접근 가능</p>
      </div>
    </div>
  );
}
