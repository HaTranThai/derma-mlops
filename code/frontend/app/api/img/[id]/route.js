const API_URL = process.env.INTERNAL_API_URL || "http://api:8000"

export const dynamic = "force-dynamic"

export async function GET(req, { params }) {
  const { id } = params
  try {
    const res = await fetch(`${API_URL}/predictions/${id}/image`, { cache: "no-store" })
    if (!res.ok) {
      return new Response(null, { status: res.status })
    }
    const buffer = await res.arrayBuffer()
    return new Response(buffer, {
      status: 200,
      headers: {
        "Content-Type": res.headers.get("content-type") || "image/jpeg",
        "Cache-Control": "private, max-age=300",
      },
    })
  } catch (err) {
    return new Response(null, { status: 502 })
  }
}
