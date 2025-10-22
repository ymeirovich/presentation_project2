import { useEffect, useState } from "react"

interface UseReportPromptOptions {
  autoLoad?: boolean
}

export function useReportPrompt(options: UseReportPromptOptions = {}) {
  const { autoLoad = true } = options
  const [prompt, setPrompt] = useState<string>("")
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!autoLoad) return

    let isMounted = true
    setLoading(true)
    setError(null)

    fetch("/api/presgen/prompts/report")
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Failed to load prompt: ${res.status}`)
        }
        return res.json()
      })
      .then((data) => {
        if (!isMounted) return
        setPrompt(data.prompt ?? "")
      })
      .catch((err) => {
        if (!isMounted) return
        console.error("Failed to load default report prompt", err)
        setError(err instanceof Error ? err.message : String(err))
        setPrompt("")
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [autoLoad])

  return {
    prompt,
    setPrompt,
    loading,
    error,
  }
}
