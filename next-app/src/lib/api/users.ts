import { User } from "@/types/meeting"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7071'

export async function getUsers(): Promise<User[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/users`, {
      headers: {
        "Accept": "application/json",
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      console.error("API Error:", {
        status: response.status,
        statusText: response.statusText,
        error: errorData
      })
      throw new Error(errorData.error || `ユーザー一覧の取得に失敗しました (${response.status})`)
    }
    
    return response.json()
  } catch (error) {
    console.error("API Request Error:", error)
    throw error
  }
} 