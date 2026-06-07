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

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Phân loại tổn thương da từ ảnh dermoscopy
        </h1>
        <div className="mt-2 flex items-center gap-2 text-sm">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              healthy ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-slate-500">
            {healthy
              ? `Model đang chạy: ${health.model_version}`
              : "API hoặc model chưa sẵn sàng"}
          </span>
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-semibold text-slate-900">Ảnh đầu vào</h2>
          <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 px-4 py-8 text-center hover:border-slate-400">
            <input type="file" accept="image/*" className="hidden" onChange={onSelect} />
            <span className="text-sm text-slate-500">
              {file ? file.name : "Bấm để chọn ảnh dermoscopy (jpg / png)"}
            </span>
          </label>

          {preview && (
            <img
              src={preview}
              alt="preview"
              onClick={() => setLightbox(preview)}
              className="mt-4 w-full cursor-pointer rounded-lg border border-slate-200 object-cover transition hover:opacity-90"
            />
          )}

          <button
            onClick={onPredict}
            disabled={!file || loading}
            className="mt-4 w-full rounded-lg bg-slate-900 px-4 py-2.5 font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? "Đang phân tích..." : "Dự đoán"}
          </button>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-semibold text-slate-900">Grad-CAM</h2>
          {result?.gradcam_base64 ? (
            <img
              src={`data:image/png;base64,${result.gradcam_base64}`}
              alt="grad-cam"
              onClick={() => setLightbox(`data:image/png;base64,${result.gradcam_base64}`)}
              className="w-full cursor-pointer rounded-lg border border-slate-200 transition hover:opacity-90"
            />
          ) : (
            <div className="flex h-48 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
              Vùng model chú ý sẽ hiển thị ở đây
            </div>
          )}
        </section>
      </div>

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <section className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg bg-slate-50 p-4">
              <div className="text-xs uppercase text-slate-400">Lớp dự đoán</div>
              <div className="mt-1 text-xl font-bold text-slate-900">{result.predicted_class}</div>
              <div className="mt-1 text-xs text-slate-500">
                {CLASS_NAMES[result.predicted_class] || ""}
              </div>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <div className="text-xs uppercase text-slate-400">Độ tin cậy</div>
              <div className="mt-1 text-xl font-bold text-slate-900">
                {(result.confidence * 100).toFixed(1)}%
              </div>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <div className="text-xs uppercase text-slate-400">Latency</div>
              <div className="mt-1 text-xl font-bold text-slate-900">{result.latency_ms} ms</div>
            </div>
          </div>

          {result.is_low_confidence && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Độ tin cậy thấp — ảnh nên được chuyên gia xem lại.
            </div>
          )}

          <h3 className="mt-6 mb-2 font-semibold text-slate-900">Top-3 dự đoán</h3>
          <div className="space-y-2">
            {result.top_k?.map((item) => (
              <div key={item.class}>
                <div className="flex justify-between text-sm">
                  <span>
                    {item.class} — {CLASS_NAMES[item.class] || item.class}
                  </span>
                  <span className="text-slate-500">{(item.probability * 100).toFixed(1)}%</span>
                </div>
                <div className="mt-1 h-2 w-full rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-slate-700"
                    style={{ width: `${Math.min(item.probability * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 text-xs text-slate-400">
            model_version={result.model_version} | data_version={result.data_version} |{" "}
            {result.prediction_id}
          </div>
          <div className="mt-3 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
            {DISCLAIMER}
          </div>
        </section>
      )}

      <Lightbox src={lightbox} onClose={() => setLightbox(null)} />
    </main>
  )
}
