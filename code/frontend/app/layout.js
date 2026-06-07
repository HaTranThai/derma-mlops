import "./globals.css"
import Link from "next/link"

export const metadata = {
  title: "Phân loại tổn thương da",
  description: "Hệ thống MLOps phân loại tổn thương da từ ảnh dermoscopy",
}

export default function RootLayout({ children }) {
  return (
    <html lang="vi">
      <body className="bg-slate-50 text-slate-800 antialiased">
        <nav className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
            <span className="font-bold text-slate-900">Skin Lesion MLOps</span>
            <Link href="/" className="text-sm text-slate-600 hover:text-slate-900">
              Dự đoán
            </Link>
            <Link href="/history" className="text-sm text-slate-600 hover:text-slate-900">
              Lịch sử
            </Link>
            <Link href="/review" className="text-sm text-slate-600 hover:text-slate-900">
              Cần review
            </Link>
            <Link href="/monitoring" className="text-sm text-slate-600 hover:text-slate-900">
              Giám sát
            </Link>
            <Link href="/admin" className="ml-auto text-sm text-slate-400 hover:text-slate-900">
              Admin
            </Link>
          </div>
        </nav>
        {children}
      </body>
    </html>
  )
}
