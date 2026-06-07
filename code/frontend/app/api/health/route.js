const API_URL = process.env.INTERNAL_API_URL || "http://api:8000"

export const dynamic = "force-dynamic"

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch (err) {
    return Response.json({ status: "unreachable", model_version: "none" }, { status: 502 })
  }
}
