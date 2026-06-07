"use client"

import { useEffect } from "react"

export default function Lightbox({ src, onClose }) {
  useEffect(() => {
    if (!src) return
    const onKey = (e) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [src, onClose])

  if (!src) return null

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
    >
      <img
        src={src}
        alt="Ảnh phóng to"
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain shadow-2xl"
      />
    </div>
  )
}
