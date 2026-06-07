"use client"

import { useEffect, useState } from "react"

import Lightbox from "../components/Lightbox"

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
    fetch("/api/reviews/queue?limit=50")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) setError(d.detail)
        else {
          setItems(d.items)
          setTotal(d.total)
        }
      })
      .catch(() => setError("Không kết nối được API"))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function confirm(item) {
    const label = labels[item.prediction_id] || item.predicted_class
    const res = await fetch("/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prediction_id: item.prediction_id,
        review_label: label,
        reviewer: "simulated",
      }),
    })
    if (res.ok) {
      setItems((prev) => prev.filter((i) => i.prediction_id !== item.prediction_id))
      setTotal((t) => Math.max(0, t - 1))
    } else {
      const d = await res.json().catch(() => ({}))
      setError(d.detail || "Không gửi được review")
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-1 text-2xl font-bold text-slate-900">Hàng chờ review</h1>
      <p className="mb-6 text-sm text-slate-500">
        Ảnh có độ tin cậy thấp cần chuyên gia xác nhận nhãn ({total} ảnh chờ)
      </p>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && <p className="text-sm text-slate-500">Đang tải...</p>}

      {!loading && items.length === 0 && (
        <p className="text-sm text-slate-500">Không có ảnh nào trong hàng chờ.</p>
      )}

      <div className="grid gap-3">
        {items.map((item) => (
          <div
            key={item.prediction_id}
            className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
          >
            {item.image_url ? (
              <img
                src={item.image_url}
                alt={item.predicted_class}
                onClick={() => setLightbox(item.image_url)}
                onError={(e) => {
                  e.currentTarget.onerror = null
                  e.currentTarget.src = PLACEHOLDER
                }}
                className="h-20 w-20 cursor-pointer rounded-lg border border-slate-200 object-cover transition hover:opacity-80"
              />
            ) : (
              <div className="h-20 w-20 rounded-lg bg-slate-100" />
            )}

            <div className="flex-1">
              <div className="text-sm text-slate-500">Model dự đoán</div>
              <div className="font-semibold text-slate-900">
                {item.predicted_class}
                <span className="ml-2 text-sm font-normal text-slate-500">
                  {CLASS_NAMES[item.predicted_class] || ""}
                </span>
                <span className="ml-2 text-sm text-amber-700">
                  ({(item.confidence * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="text-xs text-slate-400">{item.prediction_id}</div>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={labels[item.prediction_id] || item.predicted_class}
                onChange={(e) =>
                  setLabels((prev) => ({ ...prev, [item.prediction_id]: e.target.value }))
                }
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              >
                {CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {c} — {CLASS_NAMES[c]}
                  </option>
                ))}
              </select>
              <button
                onClick={() => confirm(item)}
                className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
              >
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
