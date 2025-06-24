import { MeetingSearchParams, Meeting } from "@/types/meeting"

// API_BASE_URLを明示的に定義
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

export async function searchMeetings(params: MeetingSearchParams): Promise<Meeting[]> {
  try {
    // クエリパラメータの構築
    const queryParams = new URLSearchParams()
    if (params.userId) queryParams.append("userId", params.userId)
    if (params.fromDate) queryParams.append("fromDate", params.fromDate)
    if (params.toDate) queryParams.append("toDate", params.toDate)

    // リクエストURLの構築
    const requestUrl = `${API_BASE_URL}/meetings?${queryParams.toString()}`

    const response = await fetch(requestUrl, {
      headers: {
        "Accept": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`会議データの取得に失敗しました (${response.status})`)
    }

    const data = await response.json()
    return data

  } catch (error) {
    console.error("会議データの取得に失敗:", error)
    throw error
  }
}