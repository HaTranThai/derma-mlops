const API_URL = process.env.INTERNAL_API_URL || "http://api:8000"

export const dynamic = "force-dynamic"

async function proxy(req, params, method) {
  const path = params.path.join("/")
  const { search } = new URL(req.url)
  const init = { method, headers: {}, cache: "no-store" }
  const auth = req.headers.get("authorization")
  if (auth) init.headers["Authorization"] = auth
  if (method !== "GET") {
    const body = await req.text()
    if (body) {
      init.body = body
      init.headers["Content-Type"] = "application/json"
    }
  }
  try {
    const res = await fetch(`${API_URL}/admin/${path}${search}`, init)
    const text = await res.text()
    return new Response(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    })
  } catch (err) {
    return Response.json({ detail: "Không kết nối được API" }, { status: 502 })
  }
}

export async function GET(req, { params }) {
  return proxy(req, params, "GET")
}

export async function POST(req, { params }) {
  return proxy(req, params, "POST")
}

export async function PUT(req, { params }) {
  return proxy(req, params, "PUT")
}

export async function DELETE(req, { params }) {
  return proxy(req, params, "DELETE")
}
