"use client"

import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"

import NavBar from "./NavBar"
import { getToken, getUser } from "../../lib/auth"

export default function AuthGate({ children }) {
  const pathname = usePathname()
  const router = useRouter()
  const [state, setState] = useState({ ready: false, user: null })

  useEffect(() => {
    if (pathname === "/login") {
      setState({ ready: true, user: null })
      return
    }
    if (!getToken()) {
      router.replace("/login")
      setState({ ready: false, user: null })
    } else {
      setState({ ready: true, user: getUser() })
    }
  }, [pathname, router])

  // Trang login: không cần NavBar / không chặn
  if (pathname === "/login") return <>{children}</>
  // Đang kiểm tra / chuyển hướng
  if (!state.ready) return null

  return (
    <>
      <NavBar user={state.user} />
      {children}
    </>
  )
}
