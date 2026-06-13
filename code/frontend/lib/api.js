export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

function correlationId() {
  try {
    return crypto.randomUUID()
  } catch {
    return `${Date.now()}-${Math.round(Math.random() * 1e9)}`
  }
}

export async function apiFetch(url, options = {}) {
  const isJsonBody = typeof options.body === "string"
  let res
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        "x-correlation-id": correlationId(),
        ...(isJsonBody ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    })
  } catch {
    throw new ApiError("Không kết nối được API", 0)
  }

  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const detail = data?.detail || data?.error?.message
    throw new ApiError(typeof detail === "string" ? detail : `Lỗi ${res.status}`, res.status)
  }
  return data
}
