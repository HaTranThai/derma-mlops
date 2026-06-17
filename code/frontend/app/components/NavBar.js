"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"

import { clearAuth } from "../../lib/auth"

const LINKS = [
  { href: "/", label: "Dự đoán" },
  { href: "/history", label: "Lịch sử" },
  { href: "/review", label: "Cần review" },
  { href: "/monitoring", label: "Giám sát" },
]

export default function NavBar({ user }) {
  const path = usePathname()
  const router = useRouter()
  const isActive = (h) => (h === "/" ? path === "/" : path.startsWith(h))

  function logout() {
    clearAuth()
    router.replace("/login")
  }

  return (
    <header className="sticky top-0 z-40 border-b border-white/60 bg-white/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
        <Link href="/" className="mr-3 flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-2xl bg-gradient-to-br from-teal-500 to-indigo-500 text-white shadow-lg shadow-cyan-500/30">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"
                 strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
              <path d="M3 12h3.5l1.8-4.5 3.2 9 2.2-6 1.4 1.5H21" />
            </svg>
          </span>
          <span className="hidden text-lg font-extrabold tracking-tight text-slate-800 sm:block">
            Derma<span className="gradient-text">MLOps</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-xl px-3 py-1.5 text-sm font-semibold transition ${
                isActive(l.href)
                  ? "bg-gradient-to-r from-teal-500/15 to-indigo-500/15 text-teal-700 ring-1 ring-inset ring-teal-500/25"
                  : "text-slate-500 hover:bg-slate-100/80 hover:text-slate-800"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {user?.role === "admin" && (
            <Link
              href="/admin"
              className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-semibold transition ${
                isActive("/admin") ? "bg-slate-900 text-white shadow" : "text-slate-400 hover:bg-slate-100/80 hover:text-slate-700"
              }`}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              Admin
            </Link>
          )}
          {user && (
            <span className="hidden items-center gap-1.5 rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 sm:inline-flex">
              <span className="text-slate-400">{user.role}</span>
              <b>{user.username}</b>
            </span>
          )}
          <button onClick={logout} className="btn-soft text-sm">Đăng xuất</button>
        </div>
      </div>
    </header>
  )
}
