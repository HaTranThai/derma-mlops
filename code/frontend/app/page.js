"use client"

import { useEffect, useState } from "react"

import Lightbox from "./components/Lightbox"

const CLASS_NAMES = {
  nv: "Nốt ruồi sắc tố (Melanocytic nevi)",
  mel: "U hắc tố (Melanoma)",
  bkl: "Dày sừng lành tính (Benign keratosis)",
  bcc: "Ung thư biểu mô tế bào đáy (Basal cell carcinoma)",
  akiec: "Dày sừng ánh sáng / tiền ung thư (Actinic keratoses)",
  vasc: "Tổn thương mạch máu (Vascular lesions)",
  df: "U xơ da (Dermatofibroma)",
}

// Mức quan tâm theo lớp — chỉ để tô màu tham khảo, không phải kết luận y khoa.
const RISK = {
  mel: { tone: "rose", label: "Cần chú ý" },
  bcc: { tone: "rose", label: "Cần chú ý" },
  akiec: { tone: "amber", label: "Theo dõi" },
  bkl: { tone: "emerald", label: "Lành tính" },
  nv: { tone: "emerald", label: "Lành tính" },
  df: { tone: "emerald", label: "Lành tính" },
  vasc: { tone: "emerald", label: "Lành tính" },
}

const TONE = {
  rose: "from-rose-500 to-pink-500 text-rose-600 bg-rose-50 ring-rose-200",
  amber: "from-amber-500 to-orange-500 text-amber-600 bg-amber-50 ring-amber-200",
  emerald: "from-emerald-500 to-teal-500 text-emerald-600 bg-emerald-50 ring-emerald-200",
}

const DISCLAIMER =
  "Lưu ý: Kết quả chỉ mang tính tham khảo và không thay thế chẩn đoán của bác sĩ chuyên khoa. Nếu tổn thương da có dấu hiệu bất thường, vui lòng đến cơ sở y tế để được kiểm tra."

export default function Home() {
  const [health, setHealth] = useState(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [lightbox, setLightbox] = useState(null)

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable", model_version: "none" }))
  }, [])

  function onSelect(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setResult(null)
    setError(null)
  }

  async function onPredict() {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const fd = new FormData()
      fd.append("file", file)
      const res = await fetch("/api/predict", { method: "POST", body: fd })
      const data = await res.json()
      if (!res.ok) setError(data.detail || "Đã xảy ra lỗi")
      else setResult(data)
    } catch (err) {
      setError("Không kết nối được API")
    }
    setLoading(false)
  }

  const healthy = health?.status === "ok"
  const risk = result ? RISK[result.predicted_class] || RISK.nv : null
  const tone = risk ? TONE[risk.tone] : TONE.emerald

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8 animate-fade-up">
        <span className="chip bg-teal-50 text-teal-700 ring-1 ring-teal-100">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-teal-400" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-teal-500" />
          </span>
          AI Dermoscopy · MLOps
        </span>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Phân loại <span className="gradient-text">tổn thương da</span> từ ảnh dermoscopy
        </h1>
        <div className="mt-3 flex items-center gap-2 text-sm">
          <span className={`h-2.5 w-2.5 rounded-full ${healthy ? "bg-emerald-500" : "bg-rose-500"} ${healthy ? "shadow-[0_0_0_4px_rgba(16,185,129,.15)]" : ""}`} />
          <span className="text-slate-500">
            {healthy ? `Model đang phục vụ · ${health.model_version}` : "API hoặc model chưa sẵn sàng"}
          </span>
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="glass-card animate-fade-up p-6">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-slate-900">
            <span className="grid h-7 w-7 place-items-center rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 text-white">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                <path d="M12 16V4m0 0L8 8m4-4 4 4" /><path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
              </svg>
            </span>
            Ảnh đầu vào
          </h2>
          <label className="group flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-cyan-200 bg-cyan-50/40 px-4 py-10 text-center transition hover:border-cyan-400 hover:bg-cyan-50">
            <input type="file" accept="image/*" className="hidden" onChange={onSelect} />
            <span className="mb-2 grid h-12 w-12 place-items-center rounded-2xl bg-white text-cyan-500 shadow-sm transition group-hover:scale-110">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M17 8l-5-5-5 5" /><path d="M12 3v12" />
              </svg>
            </span>
            <span className="text-sm font-medium text-slate-600">
              {file ? file.name : "Bấm để chọn ảnh dermoscopy"}
            </span>
            <span className="mt-1 text-xs text-slate-400">JPG / PNG</span>
          </label>

          {preview && (
            <img
              src={preview}
              alt="preview"
              onClick={() => setLightbox(preview)}
              className="mt-4 w-full cursor-pointer rounded-2xl border border-white object-cover shadow-md transition hover:opacity-90"
            />
          )}

          <button onClick={onPredict} disabled={!file || loading} className="btn-grad mt-5 w-full py-3 text-base">
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin-slow rounded-full border-2 border-white/40 border-t-white" />
                Đang phân tích...
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="h-5 w-5">
                  <path d="m21 21-4.3-4.3" /><circle cx="11" cy="11" r="7" />
                </svg>
                Dự đoán
              </>
            )}
          </button>
        </section>

        <section className="glass-card animate-fade-up p-6">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-slate-900">
            <span className="grid h-7 w-7 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-500 text-white">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                <circle cx="12" cy="12" r="3" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2" />
              </svg>
            </span>
            Grad-CAM <span className="text-xs font-normal text-slate-400">vùng model chú ý</span>
          </h2>
          {result?.gradcam_base64 ? (
            <img
              src={`data:image/png;base64,${result.gradcam_base64}`}
              alt="grad-cam"
              onClick={() => setLightbox(`data:image/png;base64,${result.gradcam_base64}`)}
              className="w-full cursor-pointer rounded-2xl border border-white shadow-md transition hover:opacity-90"
            />
          ) : (
            <div className="flex h-56 items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 text-center text-sm text-slate-400">
              Bản đồ nhiệt sẽ hiện ở đây<br />sau khi dự đoán
            </div>
          )}
        </section>
      </div>

      {error && (
        <div className="mt-6 flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
          {error}
        </div>
      )}

      {result && (
        <section className="glass-card mt-6 animate-fade-up p-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className={`rounded-2xl bg-gradient-to-br ${tone.split(" ").slice(0, 2).join(" ")} p-[1.5px]`}>
              <div className="rounded-2xl bg-white p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Lớp dự đoán</div>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-2xl font-extrabold text-slate-900">{result.predicted_class}</span>
                  <span className={`chip ring-1 ${tone.split(" ").slice(2).join(" ")}`}>{risk.label}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">{CLASS_NAMES[result.predicted_class] || ""}</div>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-gradient-to-br from-cyan-50 to-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Độ tin cậy</div>
              <div className="mt-1 text-2xl font-extrabold gradient-text">{(result.confidence * 100).toFixed(1)}%</div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-gradient-to-r from-teal-500 to-indigo-500" style={{ width: `${Math.min(result.confidence * 100, 100)}%` }} />
              </div>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-gradient-to-br from-indigo-50 to-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Latency</div>
              <div className="mt-1 text-2xl font-extrabold text-slate-900">{result.latency_ms}<span className="text-base font-semibold text-slate-400"> ms</span></div>
            </div>
          </div>

          {result.is_low_confidence && (
            <div className="mt-4 flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 shrink-0">
                <path d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
              </svg>
              Độ tin cậy thấp — ảnh nên được chuyên gia xem lại.
            </div>
          )}

          <h3 className="mb-3 mt-6 font-bold text-slate-900">Top-3 dự đoán</h3>
          <div className="space-y-3">
            {result.top_k?.map((item, i) => (
              <div key={item.class}>
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-slate-700">
                    <span className="font-bold text-slate-900">{item.class}</span> — {CLASS_NAMES[item.class] || item.class}
                  </span>
                  <span className="font-semibold text-slate-500">{(item.probability * 100).toFixed(1)}%</span>
                </div>
                <div className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${i === 0 ? "from-teal-500 via-cyan-500 to-indigo-500" : "from-slate-300 to-slate-400"}`}
                    style={{ width: `${Math.min(item.probability * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap gap-2 text-xs text-slate-400">
            <span className="rounded-lg bg-slate-100 px-2 py-1">model: {result.model_version}</span>
            <span className="rounded-lg bg-slate-100 px-2 py-1">data: {result.data_version}</span>
            <span className="rounded-lg bg-slate-100 px-2 py-1">{result.prediction_id}</span>
          </div>
          <div className="mt-3 flex items-start gap-2 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 h-4 w-4 shrink-0">
              <circle cx="12" cy="12" r="10" /><path d="M12 16v-4m0-4h.01" />
            </svg>
            {DISCLAIMER}
          </div>
        </section>
      )}

      <Lightbox src={lightbox} onClose={() => setLightbox(null)} />
    </main>
  )
}
