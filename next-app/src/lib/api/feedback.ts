/**
 * フィードバック関連のAPI通信を行うモジュール
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

// 会話セグメント取得API
export const getConversationSegments = async (meetingId: string | number) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/conversation/segments/${meetingId}`)
    
    // レスポンスがエラーの場合は空配列を返す
    if (!response.ok) {
      console.error(`APIエラー: HTTP ${response.status}`)
      return []
    }
    
    // 空レスポンス対策
    const text = await response.text()
    if (!text) {
      console.error('APIレスポンスが空です')
      return []
    }
    
    const data = JSON.parse(text)
    
    if (!data.success) {
      throw new Error(data.message || 'セグメント取得に失敗しました')
    }
    
    return data.segments || []
  } catch (error) {
    console.error(`会話セグメント取得エラー (meeting_id=${meetingId}):`, error)
    // エラー時には空配列を返してUIが崩れないようにする
    return []
  }
}

// コメント取得API
export const getComments = async (segmentId: string | number) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/comments/${segmentId}`)
    const data = await response.json()
    if (!data.success) {
      throw new Error(data.message || 'コメント取得に失敗しました')
    }
    return data.comments
  } catch (error) {
    console.error('コメント取得エラー:', error)
    throw error
  }
}

// ダッシュボード用の最新コメント取得API
export const getLatestComments = async (userId?: number, limit: number = 5) => {
  try {
    // userIdがundefinedの場合は不要なパラメータを送信しない
    const url = userId !== undefined 
      ? `${API_BASE_URL}/api/comments-latest?userId=${userId}&limit=${limit}`
      : `${API_BASE_URL}/api/comments-latest?limit=${limit}`;
      
    console.log('APIリクエストURL:', url) // デバッグ用ログ
    const response = await fetch(url)
    const data = await response.json()
    if (!data.success) {
      throw new Error(data.message || '最新コメント取得に失敗しました')
    }
    return data.comments
  } catch (error) {
    console.error('最新コメント取得エラー:', error)
    throw error
  }
}

// コメント追加API
export const addComment = async (
  segmentId: number,
  meetingId: number,
  content: string,
  userId?: number // デフォルト値ではなくオプショナルパラメータとする
) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        segment_id: segmentId,
        meeting_id: meetingId,
        user_id: userId,
        content
      }),
    })
    
    const data = await response.json()
    if (!data.success) {
      throw new Error(data.message || 'コメント追加に失敗しました')
    }
    return data
  } catch (error) {
    console.error('コメント追加エラー:', error)
    throw error
  }
}

// コメント既読状態更新API（一時的に無効化）
/*
export const markAsRead = async (commentId: number, userId: number = 1) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/comments/read`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        comment_id: commentId,
        user_id: userId
      }),
    })
    
    const data = await response.json()
    if (!data.success) {
      throw new Error(data.message || 'コメント既読更新に失敗しました')
    }
    return data
  } catch (error) {
    console.error('コメント既読更新エラー:', error)
    throw error
  }
}
*/

// 既読機能は一時的に無効化し、ダミー関数を提供
export const markAsRead = async (commentId: number, userId: number = 1) => {
  // 何もしないダミー関数
  console.log('既読機能は一時的に無効化されています')
  return { success: true }
}

// コメント削除API
export const deleteComment = async (commentId: number) => {
  try {
    console.log("[API] コメント削除リクエスト", { commentId })
    
    const response = await fetch(`${API_BASE_URL}/api/comments/${commentId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    // レスポンスが空の場合のエラーハンドリング
    const text = await response.text()
    if (!text) {
      throw new Error('サーバーからの応答が空です')
    }
    
    const data = JSON.parse(text)
    
    if (!response.ok) {
      throw new Error(data.message || `HTTP error! status: ${response.status}`)
    }
    
    console.log("[API] コメント削除レスポンス", data)
    return data
    
  } catch (error) {
    console.error('[API] コメント削除エラー:', error)
    throw error
  }
} 