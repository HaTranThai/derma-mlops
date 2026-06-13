"use client"

import { useEffect, useState } from "react"

import Lightbox from "../components/Lightbox"
import { apiFetch } from "../../lib/api"

const CLASS_NAMES = {
  akiec: "Dày sừng ánh sáng",
  bcc: "Ung thư biểu mô tế bào đáy",
  bkl: "Dày sừng lành tính",
  df: "U xơ da",
  mel: "U hắc tố (Melanoma)",
  nv: "Nốt ruồi sắc tố",
  vasc: "Tổn thương mạch máu",
}

const CLASSES = Object.keys(CLASS_NAMES)

const PLACEHOLDER =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80'><rect width='100%' height='100%' fill='%23e2e8f0'/></svg>"

export default function Review() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [labels, setLabels] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lightbox, setLightbox] = useState(null)

  function load() {
    setLoading(true)
    setError(null)
    apiFetch("/api/reviews/queue?limit=50")
      .then((d) => {
        setItems(d.items)
        setTotal(d.total)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function confirm(item) {
    const label = labels[item.prediction_id] || item.predicted_class
    try {
      await apiFetch("/api/reviews", {
        method: "POST",
        body: JSON.stringify({
          prediction_id: item.prediction_id,
          review_label: label,
          reviewer: "simulated",
        }),
      })
      setItems((prev) => prev.filter((i) => i.prediction_id !== item.prediction_id))
      setTotal((t) => Math.max(0, t - 1))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-6 animate-fade-up">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
          Hàng chờ <span className="gradient-text">review</span>
        </h1>
        <p className="mt-1 flex items-center gap-2 text-sm text-slate-500">
          <span className="chip bg-amber-50 text-amber-700 ring-1 ring-amber-100">{total} ảnh chờ</span>
          Ảnh độ tin cậy thấp cần chuyên gia xác nhận nhãn
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
      )}

      {loading && <p className="text-sm text-slate-500">Đang tải...</p>}

      {!loading && items.length === 0 && (
        <div className="glass-card flex flex-col items-center gap-2 p-10 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-500">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6"><path d="M20 6 9 17l-5-5" /></svg>
          </span>
          <p className="text-sm text-slate-500">Tuyệt vời — không có ảnh nào trong hàng chờ.</p>
        </div>
      )}

      <div className="grid gap-3">
        {items.map((item) => (
          <div key={item.prediction_id} className="glass-card flex items-center gap-4 p-3 transition hover:shadow-2xl">
            {item.image_url ? (
              <img
                src={item.image_url}
                alt={item.predicted_class}
                onClick={() => setLightbox(item.image_url)}
                onError={(e) => {
                  e.currentTarget.onerror = null
                  e.currentTarget.src = PLACEHOLDER
                }}
                className="h-20 w-20 cursor-pointer rounded-2xl border border-white object-cover shadow-sm transition hover:opacity-80"
              />
            ) : (
              <div className="h-20 w-20 rounded-2xl bg-slate-100" />
            )}

            <div className="flex-1">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Model dự đoán</div>
              <div className="mt-0.5 font-bold text-slate-900">
                {item.predicted_class}
                <span className="ml-2 text-sm font-normal text-slate-500">{CLASS_NAMES[item.predicted_class] || ""}</span>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span className="chip bg-amber-50 text-amber-700 ring-1 ring-amber-100">{(item.confidence * 100).toFixed(1)}%</span>
                <span className="text-xs text-slate-400">{item.prediction_id}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={labels[item.prediction_id] || item.predicted_class}
                onChange={(e) => setLabels((prev) => ({ ...prev, [item.prediction_id]: e.target.value }))}
                className="rounded-xl border border-slate-200 bg-white px-2.5 py-2 text-sm outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
              >
                {CLASSES.map((c) => (
                  <option key={c} value={c}>{c} — {CLASS_NAMES[c]}</option>
                ))}
              </select>
              <button onClick={() => confirm(item)} className="btn-grad px-4 py-2 text-sm">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="h-4 w-4"><path d="M20 6 9 17l-5-5" /></svg>
                Xác nhận
              </button>
            </div>
          </div>
        ))}
      </div>

      <Lightbox src={lightbox} onClose={() => setLightbox(null)} />
    </main>
  )
}
