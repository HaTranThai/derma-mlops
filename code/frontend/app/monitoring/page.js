"use client"

import { useEffect, useState } from "react"

const GRAFANA_URL = "http://localhost:3001"

const TONES = {
  teal: "from-teal-500 to-cyan-500",
  indigo: "from-indigo-500 to-violet-500",
  sky: "from-sky-500 to-blue-500",
  amber: "from-amber-500 to-orange-500",
  rose: "from-rose-500 to-pink-500",
  emerald: "from-emerald-500 to-teal-500",
}

function Stat({ label, value, hint, tone = "teal", icon }) {
  return (
    <div className="glass-card group p-4 transition duration-300 hover:-translate-y-1 hover:shadow-2xl">
      <div className="flex items-start justify-between">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
        <span className={`grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br ${TONES[tone]} text-white shadow-sm`}>
          {icon}
        </span>
      </div>
      <div className="mt-2 text-2xl font-extrabold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  )
}

const I = {
  total: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-5" /></svg>,
  conf: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><path d="M20 6 9 17l-5-5" /></svg>,
  time: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>,
  warn: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><path d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></svg>,
  drift: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><path d="M3 12c3-6 7 6 10 0s4-6 8 0" /></svg>,
  queue: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" /></svg>,
}

export default function Monitoring() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  function load() {
    fetch("/api/monitoring?window=200")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) setError(d.detail)
        else setData(d)
      })
      .catch(() => setError("Không kết nối được API"))
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [])

  const lowRate = data ? (data.low_confidence_rate * 100).toFixed(1) : "—"
  const driftRate = data ? (data.drift_rate * 100).toFixed(1) : "—"
  const psi = data?.population_drift_psi ?? 0
  const level = data?.population_drift_level ?? "none"
  const levelTone = level === "significant" ? "rose" : level === "moderate" ? "amber" : "emerald"

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3 animate-fade-up">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            <span className="gradient-text">Giám sát</span> hệ thống
          </h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-slate-500">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-emerald-400" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            Cập nhật mỗi 5 giây · cửa sổ {data?.window ?? 200} dự đoán gần nhất
          </p>
        </div>
        <a href={GRAFANA_URL} target="_blank" rel="noreferrer" className="btn-soft">
          Mở Grafana
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><path d="M7 17 17 7M7 7h10v10" /></svg>
        </a>
      </div>

      {error && (
        <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <Stat label="Tổng (cửa sổ)" value={data.total} tone="teal" icon={I.total} />
            <Stat label="Confidence TB" value={`${(data.avg_confidence * 100).toFixed(1)}%`} tone="emerald" icon={I.conf} />
            <Stat label="Latency TB" value={`${data.avg_latency_ms.toFixed(0)} ms`} tone="indigo" icon={I.time} />
            <Stat label="Confidence thấp" value={`${lowRate}%`} hint="cảnh báo nếu > 30%" tone={Number(lowRate) > 30 ? "rose" : "sky"} icon={I.warn} />
            <Stat label="Nghi drift (ảnh)" value={`${driftRate}%`} hint="độ sáng / độ nét" tone={Number(driftRate) > 30 ? "amber" : "sky"} icon={I.drift} />
            <Stat label="Drift phân bố (PSI)" value={psi.toFixed(3)} hint={`mức: ${level}`} tone={levelTone} icon={I.drift} />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
            <Stat label="Chờ review" value={data.review_queue} tone="amber" icon={I.queue} />
          </div>

          <h2 className="mb-3 mt-8 font-bold text-slate-900">Phân phối lớp dự đoán</h2>
          <div className="glass-card space-y-3 p-5">
            {data.class_distribution.length === 0 && (
              <p className="text-sm text-slate-400">Chưa có dữ liệu trong cửa sổ.</p>
            )}
            {data.class_distribution.map((c, i) => {
              const pct = data.total ? (c.count / data.total) * 100 : 0
              return (
                <div key={c.label}>
                  <div className="flex justify-between text-sm">
                    <span className="font-semibold text-slate-700">{c.label}</span>
                    <span className="text-slate-500">{c.count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${i % 2 ? "from-indigo-400 to-violet-500" : "from-teal-400 to-cyan-500"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </main>
  )
}
