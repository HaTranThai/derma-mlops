"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

import { apiFetch } from "../../lib/api"
import { setAuth } from "../../lib/auth"

const FIELD =
  "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"

export default function Login() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      })
      setAuth(data.access_token, { username: data.username, role: data.role })
      router.push("/")
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  return (
    <main className="mx-auto max-w-md px-4 py-20">
      <form onSubmit={submit} className="glass-card p-7 animate-fade-up">
        <span className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-teal-500 to-indigo-500 text-white">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
        </span>
        <h1 className="text-2xl font-extrabold text-slate-900">Đăng nhập <span className="gradient-text">DermaMLOps</span></h1>
        <p className="mb-5 mt-1 text-sm text-slate-500">Nhập tài khoản để sử dụng hệ thống.</p>

        <label className="block">
          <span className="text-xs font-semibold text-slate-500">Tài khoản</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} className={FIELD} autoFocus />
        </label>
        <label className="mt-3 block">
          <span className="text-xs font-semibold text-slate-500">Mật khẩu</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={FIELD} />
        </label>

        <button type="submit" disabled={loading || !username || !password} className="btn-grad mt-5 w-full py-2.5">
          {loading ? "Đang đăng nhập..." : "Đăng nhập"}
        </button>
        {error && <p className="mt-3 text-sm font-medium text-rose-600">{error}</p>}
        <p className="mt-4 text-center text-xs text-slate-400">Demo: <b>admin/admin123</b> · <b>doctor/doctor123</b></p>
      </form>
    </main>
  )
}
