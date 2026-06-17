const API_URL = process.env.INTERNAL_API_URL || "http://api:8000"

export const dynamic = "force-dynamic"

export async function GET(req) {
  const { searchParams } = new URL(req.url)
  const auth = req.headers.get("authorization")
  try {
    const res = await fetch(`${API_URL}/reviews?${searchParams.toString()}`, {
      cache: "no-store",
      headers: auth ? { Authorization: auth } : {},
    })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch (err) {
    return Response.json({ detail: "Không kết nối được API" }, { status: 502 })
  }
}

export async function POST(req) {
  try {
    const body = await req.json()
    const auth = req.headers.get("authorization")
    const res = await fetch(`${API_URL}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(auth ? { Authorization: auth } : {}) },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch (err) {
    return Response.json({ detail: "Không kết nối được API" }, { status: 502 })
  }
}
