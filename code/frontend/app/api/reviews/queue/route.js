const API_URL = process.env.INTERNAL_API_URL || "http://api:8000"

export const dynamic = "force-dynamic"

export async function GET(req) {
  const { searchParams } = new URL(req.url)
  const auth = req.headers.get("authorization")
  try {
    const res = await fetch(`${API_URL}/reviews/queue?${searchParams.toString()}`, {
      cache: "no-store",
      headers: auth ? { Authorization: auth } : {},
    })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch (err) {
    return Response.json({ detail: "Không kết nối được API" }, { status: 502 })
  }
}
