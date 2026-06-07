"use client"

import { useEffect, useState } from "react"

function StageBadge({ stage }) {
  const color =
    stage === "Production"
      ? "bg-green-100 text-green-800"
      : stage === "Staging"
        ? "bg-amber-100 text-amber-800"
        : "bg-slate-100 text-slate-600"
  return <span className={`rounded-full px-2 py-0.5 text-xs ${color}`}>{stage}</span>
}

export default function Admin() {
  const [token, setToken] = useState("")
  const [authed, setAuthed] = useState(false)
  const [models, setModels] = useState([])
  const [gate, setGate] = useState(null)
  const [runs, setRuns] = useState([])
  const [trigger, setTrigger] = useState(null)
  const [config, setConfig] = useState("")
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
        fetch("/api/admin/models", { headers: headers() }),
        fetch("/api/admin/gate", { headers: headers() }),
        fetch("/api/admin/runs", { headers: headers() }),
        fetch("/api/admin/config", { headers: headers() }),
        fetch("/api/admin/trigger-status", { headers: headers() }),
      ])
      if (m.status === 401) {
        setError("Sai admin token")
        setAuthed(false)
        return
      }
      setModels((await m.json()).versions || [])
      setGate(await g.json())
      setRuns((await r.json()).runs || [])
      setConfig(JSON.stringify(await c.json(), null, 2))
      setTrigger(await t.json())
      setAuthed(true)
    } catch {
      setError("Không kết nối được API")
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
    const res = await fetch(`/api/admin/${path}`, { method, headers: headers() })
    const data = await res.json()
    if (!res.ok) setError(data.detail || "Lỗi")
    else setMessage(`OK: ${path}`)
    loadAll()
  }

  async function saveConfig() {
    setMessage(null)
    setError(null)
    try {
      const parsed = JSON.parse(config)
      const res = await fetch("/api/admin/config", {
        method: "PUT",
        headers: headers(),
        body: JSON.stringify(parsed),
      })
      if (!res.ok) setError("Lưu config thất bại")
      else setMessage("Đã lưu config")
    } catch {
      setError("JSON không hợp lệ")
    }
  }

  if (!authed) {
    return (
      <main className="mx-auto max-w-md px-4 py-12">
        <h1 className="mb-4 text-2xl font-bold text-slate-900">Admin</h1>
        <p className="mb-3 text-sm text-slate-500">Nhập admin token để truy cập control plane.</p>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="X-Admin-Token"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          onClick={saveToken}
          className="mt-3 w-full rounded-lg bg-slate-900 px-4 py-2 font-medium text-white hover:bg-slate-700"
        >
          Vào
        </button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Admin — Control Plane</h1>
        <button
          onClick={() => {
            localStorage.removeItem("adminToken")
            setAuthed(false)
          }}
          className="text-sm text-slate-500 hover:text-slate-900"
        >
          Đăng xuất
        </button>
      </div>

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

      <section className="mb-8 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Model Registry</h2>
          <button
            onClick={() => action("seed-models")}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100"
          >
            Seed models
          </button>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400">
              <th className="pb-2">Version</th>
              <th>Tag</th>
              <th>Stage</th>
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
                <td>
                  <StageBadge stage={m.stage} />
                </td>
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

      <section className="mb-8 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Promote Gate & Retrain</h2>
          <div className="flex gap-2">
            <button
              onClick={() => action("reload-model")}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100"
            >
              Reload model
            </button>
            <button
              onClick={() => action("retrain")}
              className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
            >
              Retrain Now
            </button>
          </div>
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
                  <tr key={c.metric} className="border-t border-slate-100">
                    <td className="py-1">{c.metric}</td>
                    <td>{c.production.toFixed(3)}</td>
                    <td>{c.candidate.toFixed(3)}</td>
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
          <p className="text-sm text-slate-500">Chưa có candidate (Staging) để so sánh.</p>
        )}
      </section>

      <section className="mb-8 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Tín hiệu trigger (S1–S4)</h2>
          <button
            onClick={loadAll}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100"
          >
            Làm mới
          </button>
        </div>
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

      <section className="mb-8 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-semibold text-slate-900">Lịch sử retrain</h2>
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

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Tham số retrain (config)</h2>
          <button
            onClick={saveConfig}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100"
          >
            Lưu config
          </button>
        </div>
        <textarea
          value={config}
          onChange={(e) => setConfig(e.target.value)}
          rows={16}
          className="w-full rounded-lg border border-slate-300 p-3 font-mono text-xs"
        />
      </section>
    </main>
  )
}
