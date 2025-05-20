import { MeetingSearchParams, Meeting } from "@/types/meeting"

// API_BASE_URLを明示的に定義
const API_BASE_URL = "http://localhost:7071/api"

export async function searchMeetings(params: MeetingSearchParams): Promise<Meeting[]> {
  console.log("🧭 searchMeetings 実行開始")
  console.log("📍 API_BASE_URL:", API_BASE_URL)
  console.log("📥 params:", params)

  try {
    // クエリパラメータの構築
    const queryParams = new URLSearchParams()
    if (params.userId) queryParams.append("userId", params.userId)
    if (params.fromDate) queryParams.append("fromDate", params.fromDate)
    if (params.toDate) queryParams.append("toDate", params.toDate)

    // リクエストURLの構築
    const baseUrl = `${API_BASE_URL}/meetings`
    console.log("🔨 ベースURL:", baseUrl)

    const requestUrl = `${baseUrl}?${queryParams.toString()}`
    console.log("🌐 最終リクエストURL:", requestUrl)

    const response = await fetch(requestUrl, {
      headers: {
        "Accept": "application/json",
      },
    })

    console.log("📦 ステータス:", response.status)
    console.log("📦 レスポンスヘッダー:", Object.fromEntries(response.headers.entries()))

    // レスポンスの生データを取得
    const rawBody = await response.text()
    console.log("📦 レスポンス生データ:", rawBody)

    // JSONパースを試行
    let data: Meeting[]
    try {
      data = JSON.parse(rawBody)
      console.log("📦 パース後のオブジェクト:", data)
    } catch (e) {
      console.error("❌ JSONパースエラー:", e)
      throw new Error("JSONのパースに失敗しました")
    }

    if (!response.ok) {
      console.error("❌ API Error:", {
        status: response.status,
        statusText: response.statusText,
        url: requestUrl,
        data: data
      })
      throw new Error(`会議データの取得に失敗しました (${response.status})`)
    }

    return data
  } catch (error) {
    console.error("❌ API Request Error:", error)
    throw error
  }
}