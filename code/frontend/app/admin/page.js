"use client"

import { useEffect, useState } from "react"

import { apiFetch, ApiError } from "../../lib/api"

function StageBadge({ stage }) {
  const color =
    stage === "Production"
      ? "bg-green-100 text-green-800"
      : stage === "Staging"
        ? "bg-amber-100 text-amber-800"
        : "bg-slate-100 text-slate-600"
  return <span className={`rounded-full px-2 py-0.5 text-xs ${color}`}>{stage}</span>
}

const ARCHS = ["efficientnet_b0", "resnet50", "mobilenet_v3_large"]
const FIELD =
  "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"

function Num({ label, value, onChange, step, hint }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-slate-500">{label}</span>
      <input
        type="number"
        step={step || "any"}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className={FIELD}
      />
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  )
}

function Txt({ label, value, onChange, hint }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-slate-500">{label}</span>
      <input value={value ?? ""} onChange={(e) => onChange(e.target.value)} className={FIELD} />
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  )
}

function Toggle({ label, value, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className="flex items-center gap-2 text-sm font-medium text-slate-600"
    >
      <span
        className={`relative h-6 w-11 rounded-full transition ${
          value ? "bg-gradient-to-r from-teal-500 to-indigo-500" : "bg-slate-200"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${
            value ? "left-[22px]" : "left-0.5"
          }`}
        />
      </span>
      {label}
    </button>
  )
}

function fmtTime(ms) {
  if (!ms) return "—"
  const d = new Date(ms)
  const p = (n) => String(n).padStart(2, "0")
  return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function StatusPill({ label, value, tone = "slate" }) {
  const tones = {
    green: "bg-emerald-50 text-emerald-700 ring-emerald-100",
    amber: "bg-amber-50 text-amber-700 ring-amber-100",
    indigo: "bg-indigo-50 text-indigo-700 ring-indigo-100",
    slate: "bg-slate-100 text-slate-600 ring-slate-200",
  }
  return (
    <span className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium ring-1 ring-inset ${tones[tone]}`}>
      <span className="text-slate-400">{label}</span>
      <b>{value}</b>
    </span>
  )
}

function InfoTip({ text }) {
  return (
    <span className="group/tip relative inline-flex align-middle">
      <span
        role="button"
        tabIndex={0}
        aria-label="Giải thích"
        className="grid h-5 w-5 cursor-help place-items-center rounded-full bg-slate-100 text-[11px] font-bold text-slate-400 transition hover:bg-teal-100 hover:text-teal-600"
      >
        !
      </span>
      <span className="pointer-events-none invisible absolute left-0 top-7 z-30 w-80 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-normal leading-relaxed text-slate-600 opacity-0 shadow-xl transition-all duration-150 group-hover/tip:visible group-hover/tip:opacity-100">
        {text}
      </span>
    </span>
  )
}

function SectionHead({ title, desc, right }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
        {title}
        {desc && <InfoTip text={desc} />}
      </h2>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  )
}

export default function Admin() {
  const [token, setToken] = useState("")
  const [authed, setAuthed] = useState(false)
  const [models, setModels] = useState([])
  const [gate, setGate] = useState(null)
  const [runs, setRuns] = useState([])
  const [trigger, setTrigger] = useState(null)
  const [config, setConfig] = useState(null)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const saved = localStorage.getItem("adminToken")
    if (saved) {
      setToken(saved)
      setAuthed(true)
    }
  }, [])

  function headers() {
    return { "X-Admin-Token": token, "Content-Type": "application/json" }
  }

  async function loadAll() {
    setError(null)
    try {
      const [m, g, r, c, t] = await Promise.all([
        apiFetch("/api/admin/models", { headers: headers() }),
        apiFetch("/api/admin/gate", { headers: headers() }),
        apiFetch("/api/admin/runs", { headers: headers() }),
        apiFetch("/api/admin/config", { headers: headers() }),
        apiFetch("/api/admin/trigger-status", { headers: headers() }),
      ])
      setModels(m.versions || [])
      setGate(g)
      setRuns(r.runs || [])
      setConfig(c)
      setTrigger(t)
      setAuthed(true)
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError("Sai admin token")
        setAuthed(false)
      } else {
        setError(e.message)
      }
    }
  }

  useEffect(() => {
    if (authed && token) loadAll()
  }, [authed])

  function saveToken() {
    localStorage.setItem("adminToken", token)
    setAuthed(true)
    loadAll()
  }

  async function action(path, method = "POST") {
    setMessage(null)
    setError(null)
    try {
      await apiFetch(`/api/admin/${path}`, { method, headers: headers() })
      setMessage(`OK: ${path}`)
    } catch (e) {
      setError(e.message)
    }
    loadAll()
  }

  async function ingestReviews() {
    setError(null)
    setMessage("Đang đưa ảnh review vào tập train + DVC (có thể mất vài chục giây)...")
    try {
      const data = await apiFetch("/api/admin/ingest-reviews", { method: "POST", headers: headers() })
      if (data.note === "khong co review moi") {
        setMessage("Không có review mới để đưa vào tập train.")
      } else {
        const dv = data.data_version ? data.data_version.slice(0, 12) : "—"
        const extra = []
        if (data.leaked) extra.push(`${data.leaked} bị loại (trùng val/test)`)
        if (data.invalid) extra.push(`${data.invalid} ảnh lỗi/sai nhãn`)
        setMessage(`Đã đưa ${data.ingested} ảnh vào train${extra.length ? " | " + extra.join(", ") : ""} | dvc: ${data.dvc} | data version: ${dv}`)
      }
    } catch (e) {
      setError(e.message)
    }
    loadAll()
  }

  async function saveConfig() {
    setMessage(null)
    setError(null)
    try {
      await apiFetch("/api/admin/config", {
        method: "PUT",
        headers: headers(),
        body: JSON.stringify(config),
      })
      setMessage("Đã lưu config")
    } catch (e) {
      setError(e.message)
    }
  }

  const setRoot = (k, v) => setConfig((c) => ({ ...c, [k]: v }))
  const setTrig = (k, v) => setConfig((c) => ({ ...c, trigger: { ...c.trigger, [k]: v } }))
  const setSmoke = (k, v) => setConfig((c) => ({ ...c, smoke: { ...c.smoke, [k]: v } }))
  function toggleArch(a) {
    setConfig((c) => {
      const cur = c.smoke.archs || []
      const next = cur.includes(a) ? cur.filter((x) => x !== a) : [...cur, a]
      return { ...c, smoke: { ...c.smoke, archs: next.length ? next : null } }
    })
  }

  if (!authed) {
    return (
      <main className="mx-auto max-w-md px-4 py-16">
        <div className="glass-card p-7 animate-fade-up">
          <span className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 text-white">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
          </span>
          <h1 className="text-2xl font-extrabold text-slate-900">Admin <span className="gradient-text">Control Plane</span></h1>
          <p className="mb-4 mt-1 text-sm text-slate-500">Nhập admin token để truy cập.</p>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="X-Admin-Token"
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
          />
          <button onClick={saveToken} className="btn-grad mt-3 w-full py-2.5">Vào</button>
          {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
        </div>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-3 flex items-center justify-between animate-fade-up">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Admin <span className="gradient-text">Control Plane</span></h1>
        <button
          onClick={() => {
            localStorage.removeItem("adminToken")
            setAuthed(false)
          }}
          className="btn-soft text-sm"
        >
          Đăng xuất
        </button>
      </div>

      {(() => {
        const prod = models.find((m) => m.stage === "Production")
        return (
          <div className="mb-7 flex flex-wrap items-center gap-2.5 animate-fade-up">
            <StatusPill label="Production" value={prod ? `${prod.tag} · ${prod.arch || "—"}` : "chưa có"} tone={prod ? "green" : "slate"} />
            <StatusPill label="Auto-trigger" value={config?.auto_trigger_enabled ? "BẬT" : "TẮT"} tone={config?.auto_trigger_enabled ? "green" : "slate"} />
            <StatusPill label="Chế độ" value={config?.mode || "—"} tone="indigo" />
            <StatusPill label="Tổng version" value={models.length} tone="slate" />
          </div>
        )
      })()}

      {message && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="glass-card mb-8 p-5">
        <SectionHead
          title="Model Registry"
          desc={<>Mọi version model (từ MLflow). <b className="text-emerald-700">Production</b> = đang serve · <b className="text-amber-700">Staging</b> = candidate chờ duyệt. Nút <b>Promote</b> = đưa lên Production <b>thủ công</b> (bỏ qua gate).</>}
          right={<button onClick={() => action("seed-models")} className="btn-soft text-sm">Seed models</button>}
        />
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400">
              <th className="pb-2">Version</th>
              <th>Tag</th>
              <th>Kiến trúc</th>
              <th>Stage</th>
              <th>Tín hiệu</th>
              <th>Thời gian</th>
              <th>macro_f1</th>
              <th>mel_recall</th>
              <th>accuracy</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => (
              <tr key={m.version} className="border-t border-slate-100">
                <td className="py-2">{m.version}</td>
                <td>{m.tag}</td>
                <td className="font-mono text-xs text-slate-500">{m.arch || "—"}</td>
                <td>
                  <StageBadge stage={m.stage} />
                </td>
                <td>
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-600">
                    {m.trigger || "—"}
                  </span>
                </td>
                <td className="whitespace-nowrap text-xs text-slate-500">{fmtTime(m.created)}</td>
                <td>{(m.metrics.macro_f1 ?? 0).toFixed(3)}</td>
                <td>{(m.metrics.melanoma_recall ?? 0).toFixed(3)}</td>
                <td>{(m.metrics.accuracy ?? 0).toFixed(3)}</td>
                <td className="text-right">
                  {m.stage !== "Production" && (
                    <button
                      onClick={() => action(`promote/${m.version}`)}
                      className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100"
                    >
                      Promote
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="glass-card mb-8 p-5">
        <SectionHead
          title="Huấn luyện & Duyệt model"
          desc={<><b>Retrain Now</b> train candidate mới (theo phần Cấu hình bên dưới) → so với Production qua <b>Gate</b> → đạt thì tự promote. <b>Reload model</b> dùng sau khi promote để serve model mới.</>}
        />
        <div className="mb-5 flex flex-wrap gap-2.5">
          <button onClick={() => action("retrain")} className="btn-grad px-4 py-2 text-sm" title="Train candidate ngay rồi gate">Retrain Now</button>
          <button onClick={ingestReviews} className="btn-soft text-sm" title="Tải ảnh đã review từ MinIO vào data/subset + dvc push">Đưa review vào tập train</button>
          <button onClick={() => action("eval-production-val")} className="btn-soft text-sm" title="Chấm model Production trên data/val (~vài phút)">Chấm Prod/val</button>
          <button onClick={() => action("reload-model")} className="btn-soft text-sm" title="Nạp lại model Production từ MinIO — dùng sau khi promote">Reload model</button>
        </div>
        {gate?.gate ? (
          <div>
            <p className="mb-2 text-sm">
              Production <b>{gate.production?.tag}</b> vs Candidate <b>{gate.candidate?.tag}</b> →{" "}
              <span className={gate.gate.passed ? "text-green-700" : "text-red-700"}>
                {gate.gate.passed ? "ĐẠT (sẽ promote)" : "KHÔNG ĐẠT (giữ production)"}
              </span>
            </p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400">
                  <th className="pb-1">Metric</th>
                  <th>Production</th>
                  <th>Candidate</th>
                  <th>Rule</th>
                  <th>Kết quả</th>
                </tr>
              </thead>
              <tbody>
                {gate.gate.checks.map((c) => (
                  <tr key={`${c.metric}-${c.rule}`} className="border-t border-slate-100">
                    <td className="py-1">{c.metric}</td>
                    <td>{c.rule === "min" ? `≥ ${(c.floor ?? 0).toFixed(2)}` : (c.production ?? 0).toFixed(3)}</td>
                    <td>{(c.candidate ?? 0).toFixed(3)}</td>
                    <td className="text-slate-500">{c.rule}</td>
                    <td className={c.passed ? "text-green-700" : "text-red-700"}>
                      {c.passed ? "pass" : "fail"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-center text-sm text-slate-500">
            Chưa có candidate (Staging) để so sánh.
            <div className="mt-1 text-xs">
              Bấm <b>Retrain Now</b> để train candidate mới, hoặc chuyển <b>Chế độ → artifact</b> (phần Cấu hình) nếu đã có model ở Staging.
            </div>
          </div>
        )}
      </section>

      <section className="glass-card mb-8 p-5">
        <SectionHead
          title="Tự động hoá — Tín hiệu (S1–S4)"
          desc={<>Khi nào hệ thống <b>TỰ</b> retrain. Bật/tắt + chỉnh ngưỡng ở phần <b>Cấu hình</b> bên dưới. Cột "Chi tiết" cho biết còn thiếu bao nhiêu để tín hiệu kêu.</>}
          right={<button onClick={loadAll} className="btn-soft text-sm">Làm mới</button>}
        />
        {trigger ? (
          <div>
            <p className="mb-3 text-sm">
              Auto-trigger:{" "}
              <span className={trigger.enabled ? "text-green-700" : "text-slate-500"}>
                {trigger.enabled ? "BẬT" : "TẮT"}
              </span>{" "}
              · Cooldown: {trigger.cooldown_ok ? "sẵn sàng" : "đang chờ"} · Sẽ kích hoạt:{" "}
              <b className={trigger.would_trigger ? "text-red-700" : "text-slate-600"}>
                {trigger.would_trigger ? "CÓ" : "không"}
              </b>
            </p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400">
                  <th className="pb-2">Tín hiệu</th>
                  <th>Mô tả</th>
                  <th>Trạng thái</th>
                  <th>Chi tiết</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["S1", "Đủ dữ liệu review mới"],
                  ["S2", "Drift / confidence thấp"],
                  ["S3", "Hiệu năng giảm (online)"],
                ].map(([code, label]) => {
                  const c = trigger.checks?.[code] || {}
                  const { fired, ...rest } = c
                  return (
                    <tr key={code} className="border-t border-slate-100 align-top">
                      <td className="py-2 font-medium">{code}</td>
                      <td>{label}</td>
                      <td>
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs ${
                            fired ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          {fired ? "BẬT" : "tắt"}
                        </span>
                      </td>
                      <td className="font-mono text-xs text-slate-500">
                        {Object.entries(rest)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(" · ")}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-slate-500">
              <b>S4 — Định kỳ:</b> do Prefect cron tự lên lịch (xem <code>schedule_cron</code> trong config bên dưới),
              không nằm trong vòng lặp này. Đổi lịch xong cần restart <code>prefect-worker</code>.
            </p>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Đang tải…</p>
        )}
      </section>

      <section className="glass-card mb-8 p-5">
        <SectionHead
          title="Lịch sử retrain"
          desc={<>Các lần retrain đã chạy: tín hiệu kích · mode · kết quả gate · có promote không. (<code>skip_no_new_data</code> = tín hiệu kêu nhưng data không đổi nên bỏ qua.)</>}
        />
        {runs.length === 0 ? (
          <p className="text-sm text-slate-500">Chưa có lần retrain nào.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400">
                <th className="pb-2">#</th>
                <th>Thời gian</th>
                <th>Trigger</th>
                <th>Mode</th>
                <th>Gate</th>
                <th>Promoted</th>
                <th>Chuyển</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t border-slate-100">
                  <td className="py-1">{r.id}</td>
                  <td className="text-slate-500">{new Date(r.triggered_at).toLocaleString()}</td>
                  <td>{r.trigger_reason}</td>
                  <td>{r.mode}</td>
                  <td>{r.gate_passed === null ? "—" : r.gate_passed ? "pass" : "fail"}</td>
                  <td>{r.promoted ? "✓" : "—"}</td>
                  <td className="text-slate-500">
                    {r.production_tag} → {r.candidate_tag}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="glass-card p-5">
        <SectionHead
          title="Cấu hình retrain"
          desc={<>Áp cho <b>mọi</b> retrain (Retrain Now + tín hiệu tự động). Phần <b>Smoke retrain</b> = train thế nào · phần <b>Tín hiệu trigger</b> = ngưỡng để tự kêu. Nhớ bấm <b>Lưu</b>.</>}
          right={<button onClick={saveConfig} className="btn-grad px-4 py-2 text-sm">Lưu config</button>}
        />

        {!config ? (
          <p className="text-sm text-slate-500">Đang tải…</p>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-wrap items-end gap-6">
              <label className="block">
                <span className="text-xs font-semibold text-slate-500">Chế độ retrain</span>
                <select value={config.mode} onChange={(e) => setRoot("mode", e.target.value)} className={`${FIELD} w-60`}>
                  <option value="smoke">smoke (train model mới)</option>
                  <option value="artifact">artifact (chỉ duyệt model có sẵn)</option>
                </select>
              </label>
              <div className="pb-2">
                <Toggle label="Tự động trigger (auto)" value={config.auto_trigger_enabled} onChange={(v) => setRoot("auto_trigger_enabled", v)} />
              </div>
            </div>

            <div>
              <h3 className="mb-2 text-sm font-bold text-slate-700">Tín hiệu trigger</h3>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <Num label="S1 · review tối thiểu" value={config.trigger.min_reviewed_images} onChange={(v) => setTrig("min_reviewed_images", v)} />
                <Num label="S2 · ngưỡng drift" value={config.trigger.drift_rate_threshold} onChange={(v) => setTrig("drift_rate_threshold", v)} step="0.05" />
                <Num label="S2 · ngưỡng low-conf" value={config.trigger.low_confidence_rate_threshold} onChange={(v) => setTrig("low_confidence_rate_threshold", v)} step="0.05" />
                <Num label="S2 · mẫu tối thiểu" value={config.trigger.min_samples} onChange={(v) => setTrig("min_samples", v)} />
                <Num label="S2 · cửa sổ" value={config.trigger.auto_window} onChange={(v) => setTrig("auto_window", v)} />
                <Num label="S3 · accuracy tối thiểu" value={config.trigger.perf_min_accuracy} onChange={(v) => setTrig("perf_min_accuracy", v)} step="0.05" />
                <Num label="S3 · review tối thiểu" value={config.trigger.perf_min_reviews} onChange={(v) => setTrig("perf_min_reviews", v)} />
                <Num label="S3 · cửa sổ" value={config.trigger.perf_window} onChange={(v) => setTrig("perf_window", v)} />
                <Num label="Cooldown (phút)" value={config.trigger.cooldown_minutes} onChange={(v) => setTrig("cooldown_minutes", v)} />
                <Num label="Chu kỳ kiểm tra (giây)" value={config.trigger.auto_check_interval_seconds} onChange={(v) => setTrig("auto_check_interval_seconds", v)} />
                <Txt label="S4 · lịch cron" value={config.trigger.schedule_cron} onChange={(v) => setTrig("schedule_cron", v)} hint="đổi xong restart prefect-worker" />
              </div>
            </div>

            <div>
              <h3 className="mb-2 text-sm font-bold text-slate-700">Smoke retrain (train thật)</h3>
              <div className="mb-3">
                <span className="text-xs font-semibold text-slate-500">
                  Kiến trúc train để so sánh <span className="font-normal text-slate-400">(chọn ≥1; bỏ trống = dùng model đơn bên dưới)</span>
                </span>
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {ARCHS.map((a) => {
                    const on = (config.smoke.archs || []).includes(a)
                    return (
                      <button
                        key={a}
                        type="button"
                        onClick={() => toggleArch(a)}
                        className={`rounded-xl px-3 py-1.5 text-sm font-medium transition ${
                          on
                            ? "bg-gradient-to-r from-teal-500/15 to-indigo-500/15 text-teal-700 ring-1 ring-inset ring-teal-500/30"
                            : "border border-slate-200 text-slate-500 hover:bg-slate-100"
                        }`}
                      >
                        {on ? "✓ " : ""}{a}
                      </button>
                    )
                  })}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <label className="block">
                  <span className="text-xs font-semibold text-slate-500">Model đơn</span>
                  <select value={config.smoke.arch} onChange={(e) => setSmoke("arch", e.target.value)} className={FIELD}>
                    {ARCHS.map((a) => (
                      <option key={a} value={a}>{a}</option>
                    ))}
                  </select>
                </label>
                <Num label="Ảnh/lớp (trống = tất cả)" value={config.smoke.subset_per_class} onChange={(v) => setSmoke("subset_per_class", v)} />
                <Num label="Epochs" value={config.smoke.epochs} onChange={(v) => setSmoke("epochs", v)} />
                <Num label="Batch size" value={config.smoke.batch_size} onChange={(v) => setSmoke("batch_size", v)} />
                <Num label="Learning rate" value={config.smoke.learning_rate} onChange={(v) => setSmoke("learning_rate", v)} step="0.0001" />
                <Num label="Val fraction" value={config.smoke.val_fraction} onChange={(v) => setSmoke("val_fraction", v)} step="0.05" />
                <Num label="Seed" value={config.smoke.seed} onChange={(v) => setSmoke("seed", v)} />
                <Txt label="Tag phiên bản" value={config.smoke.version_tag} onChange={(v) => setSmoke("version_tag", v)} />
              </div>
              <div className="mt-3">
                <Toggle label="Freeze backbone (chỉ train head)" value={config.smoke.freeze_backbone} onChange={(v) => setSmoke("freeze_backbone", v)} />
              </div>
            </div>

            <details className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
              <summary className="cursor-pointer text-xs font-semibold text-slate-500">Nâng cao — JSON đầy đủ (gồm promote_rules)</summary>
              <pre className="mt-2 overflow-auto rounded-lg bg-white p-3 text-[11px] text-slate-600">{JSON.stringify(config, null, 2)}</pre>
            </details>
          </div>
        )}
      </section>
    </main>
  )
}
