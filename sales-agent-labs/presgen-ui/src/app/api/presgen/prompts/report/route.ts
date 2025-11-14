import { NextRequest, NextResponse } from "next/server"

const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""

export async function GET(_request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_API_URL}/prompts/report`, {
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    })

    if (!response.ok) {
      const text = await response.text()
      return NextResponse.json(
        { ok: false, error: `Backend error: ${response.status}`, detail: text },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json({ ok: true, ...data })
  } catch (error) {
    console.error("Failed to load report prompt", error)
    return NextResponse.json(
      { ok: false, error: "Failed to load report prompt" },
      { status: 502 }
    )
  }
}
