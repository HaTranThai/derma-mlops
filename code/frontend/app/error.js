"use client"

export default function Error({ error, reset }) {
  return (
    <main className="mx-auto max-w-2xl px-4 py-20">
      <div className="glass-card p-10 text-center animate-fade-up">
        <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-rose-50 text-rose-500">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-7 w-7">
            <path d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
          </svg>
        </div>
        <h1 className="text-2xl font-extrabold text-slate-900">Đã xảy ra lỗi</h1>
        <p className="mt-2 text-sm text-slate-500">
          Giao diện gặp sự cố khi hiển thị. Bạn thử lại, nếu vẫn lỗi hãy tải lại trang.
        </p>
        {error?.digest && <p className="mt-1 text-xs text-slate-400">Mã lỗi: {error.digest}</p>}
        <div className="mt-6 flex justify-center gap-3">
          <button onClick={() => reset()} className="btn-grad px-5 py-2.5 text-sm">
            Thử lại
          </button>
          <button onClick={() => window.location.reload()} className="btn-soft text-sm">
            Tải lại trang
          </button>
        </div>
      </div>
    </main>
  )
}
