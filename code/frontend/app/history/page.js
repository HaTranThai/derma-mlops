"use client"

import { useEffect, useState } from "react"

import Lightbox from "../components/Lightbox"

const CLASS_NAMES = {
  nv: "Nốt ruồi sắc tố",
  mel: "U hắc tố (Melanoma)",
  bkl: "Dày sừng lành tính",
  bcc: "Ung thư biểu mô tế bào đáy",
  akiec: "Dày sừng ánh sáng",
  vasc: "Tổn thương mạch máu",
  df: "U xơ da",
}

const LIMIT = 20

const PLACEHOLDER =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80'><rect width='100%' height='100%' fill='%23e2e8f0'/></svg>"

export default function History() {
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [lightbox, setLightbox] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/predictions?page=${page}&limit=${LIMIT}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) setError(d.detail)
        else setData(d)
      })
      .catch(() => setError("Không kết nối được API"))
      .finally(() => setLoading(false))
  }, [page])

  const totalPages = data ? Math.max(1, Math.ceil(data.total / LIMIT)) : 1

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-6 animate-fade-up">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
          Lịch sử <span className="gradient-text">dự đoán</span>
        </h1>
        <p className="mt-1 text-sm text-slate-500">{data ? `Tổng cộng ${data.total} bản ghi` : ""}</p>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">{error}</div>
      )}

      {loading && <p className="text-sm text-slate-500">Đang tải...</p>}

      {data && data.items.length === 0 && (
        <div className="glass-card p-10 text-center text-sm text-slate-500">
          Chưa có dự đoán nào. Hãy thử upload ảnh ở trang Dự đoán.
        </div>
      )}

      <div className="grid gap-3">
        {data?.items.map((item) => (
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
                className="h-16 w-16 cursor-pointer rounded-2xl border border-white object-cover shadow-sm transition hover:opacity-80"
              />
            ) : (
              <div className="h-16 w-16 rounded-2xl bg-slate-100" />
            )}
            <div className="flex-1">
              <div className="font-bold text-slate-900">
                {item.predicted_class}
                <span className="ml-2 text-sm font-normal text-slate-500">{CLASS_NAMES[item.predicted_class] || ""}</span>
              </div>
              <div className="mt-0.5 text-sm text-slate-500">
                Tin cậy <span className="font-semibold text-slate-700">{(item.confidence * 100).toFixed(1)}%</span> · {item.latency_ms} ms · {item.model_version}
              </div>
              <div className="text-xs text-slate-400">{item.prediction_id}</div>
            </div>
            {item.is_low_confidence && (
              <span className="chip bg-amber-50 text-amber-700 ring-1 ring-amber-100">Tin cậy thấp</span>
            )}
          </div>
        ))}
      </div>

      {data && data.total > LIMIT && (
        <div className="mt-6 flex items-center justify-center gap-3">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="btn-soft disabled:opacity-40">
            ← Trước
          </button>
          <span className="rounded-xl bg-white/70 px-3 py-1.5 text-sm font-semibold text-slate-600 backdrop-blur">
            {page} / {totalPages}
          </span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="btn-soft disabled:opacity-40">
            Sau →
          </button>
        </div>
      )}

      <Lightbox src={lightbox} onClose={() => setLightbox(null)} />
    </main>
  )
}
