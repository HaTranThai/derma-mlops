import "./globals.css"

import AuthGate from "./components/AuthGate"

export const metadata = {
  title: "DermaMLOps — Phân loại tổn thương da",
  description: "Hệ thống MLOps phân loại tổn thương da từ ảnh dermoscopy",
}

export default function RootLayout({ children }) {
  return (
    <html lang="vi">
      <body className="font-sans">
        <AuthGate>{children}</AuthGate>
        <footer className="mx-auto max-w-6xl px-4 pb-10 pt-6 text-center text-xs text-slate-400">
          DermaMLOps · Công cụ hỗ trợ tham khảo — không thay thế chẩn đoán của bác sĩ chuyên khoa.
        </footer>
      </body>
    </html>
  )
}
