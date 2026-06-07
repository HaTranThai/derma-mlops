"use client"

import { useEffect, useState } from "react"

const GRAFANA_URL = "http://localhost:3001"

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs uppercase text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  )
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

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Giám sát</h1>
          <p className="text-sm text-slate-500">
            Cập nhật mỗi 5 giây · cửa sổ {data?.window ?? 200} dự đoán gần nhất
          </p>
        </div>
        <a
          href={GRAFANA_URL}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
        >
          Mở Grafana →
        </a>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <Stat label="Tổng (cửa sổ)" value={data.total} />
            <Stat label="Confidence TB" value={`${(data.avg_confidence * 100).toFixed(1)}%`} />
            <Stat label="Latency TB" value={`${data.avg_latency_ms.toFixed(0)} ms`} />
            <Stat label="Tỷ lệ confidence thấp" value={`${lowRate}%`} hint="cảnh báo nếu > 30%" />
            <Stat label="Tỷ lệ nghi drift" value={`${driftRate}%`} />
            <Stat label="Chờ review" value={data.review_queue} />
          </div>

          <h2 className="mb-3 mt-8 font-semibold text-slate-900">Phân phối lớp dự đoán</h2>
          <div className="space-y-2">
            {data.class_distribution.map((c) => {
              const pct = data.total ? (c.count / data.total) * 100 : 0
              return (
                <div key={c.label}>
                  <div className="flex justify-between text-sm">
                    <span>{c.label}</span>
                    <span className="text-slate-500">
                      {c.count} ({pct.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-slate-700" style={{ width: `${pct}%` }} />
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
