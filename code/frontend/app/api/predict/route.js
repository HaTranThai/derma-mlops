const API_URL = process.env.INTERNAL_API_URL || "http://api:8000"

export const dynamic = "force-dynamic"

export async function POST(req) {
  try {
    const formData = await req.formData()
    const file = formData.get("file")
    if (!file) {
      return Response.json({ detail: "Thiếu file ảnh" }, { status: 400 })
    }
    const upstream = new FormData()
    upstream.append("file", file, file.name || "upload.jpg")
    const auth = req.headers.get("authorization")
    const res = await fetch(`${API_URL}/predict`, {
      method: "POST",
      body: upstream,
      headers: auth ? { Authorization: auth } : {},
    })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch (err) {
    return Response.json({ detail: "Không kết nối được API" }, { status: 502 })
  }
}
