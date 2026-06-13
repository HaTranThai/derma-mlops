"use client"

export default function GlobalError({ error, reset }) {
  return (
    <html lang="vi">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          display: "flex",
          minHeight: "100vh",
          alignItems: "center",
          justifyContent: "center",
          margin: 0,
          background: "#f8fafc",
          color: "#0f172a",
        }}
      >
        <div style={{ textAlign: "center", padding: "2rem" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800 }}>Đã xảy ra lỗi hệ thống</h1>
          <p style={{ color: "#64748b", marginTop: "0.5rem" }}>Vui lòng tải lại trang.</p>
          {error?.digest && (
            <p style={{ color: "#94a3b8", fontSize: "0.75rem" }}>Mã lỗi: {error.digest}</p>
          )}
          <button
            onClick={() => reset()}
            style={{
              marginTop: "1.25rem",
              padding: "0.6rem 1.25rem",
              borderRadius: "0.75rem",
              border: "none",
              background: "#0d9488",
              color: "white",
              cursor: "pointer",
            }}
          >
            Thử lại
          </button>
        </div>
      </body>
    </html>
  )
}
