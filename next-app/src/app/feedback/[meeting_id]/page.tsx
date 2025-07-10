'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { ArrowLeft, MessageCircle } from 'lucide-react'
import Link from 'next/link'
import { getConversationSegments, getComments, addComment as apiAddComment, markAsRead, deleteComment } from '@/lib/api/feedback'
import { useAuth } from '@/hooks/useAuth'
import ChatMessage from '@/components/ChatMessage'
import AudioSegmentPlayer from '@/components/AudioSegmentPlayer'
import { CommentList } from '@/components/feedback/comment-list'
import AudioController from '@/components/AudioController'

interface Speaker {
  speaker_id: number
  speaker_name: string
  speaker_role?: string
}

interface ConversationSegment {
  segment_id: number
  user_id: number
  speaker_id: number
  meeting_id: number
  content: string
  file_name: string
  file_path: string
  file_size: number
  duration_seconds: number
  status: string
  inserted_datetime: string
  updated_datetime: string
  speaker_name?: string
  speaker_role?: string
  start_time: number
  end_time: number
  audio_path?: string
}

interface CommentReader {
  reader_id: number
  read_datetime: string
}

interface Comment {
  comment_id: number
  segment_id: number
  meeting_id: number
  user_id: number
  user_name: string
  content: string
  inserted_datetime: string
  updated_datetime: string
  readers: CommentReader[]
}

interface Meeting {
  meeting_id: number
  client_company_name: string
  client_contact_name: string
  meeting_datetime: string
}

export default function FeedbackPage() {
  const params = useParams()
  const meetingId = params.meeting_id as string
  const { user } = useAuth()
  
  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [segments, setSegments] = useState<ConversationSegment[]>([])
  const [comments, setComments] = useState<Record<number, Comment[]>>({})
  const [newComments, setNewComments] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  
  // ログインユーザーID（実際のユーザーIDまたはデフォルト値として1）
  const userId = user?.user_id || 1

  useEffect(() => {
    fetchMeeting()
    fetchSegments()
  }, [meetingId, userId])

  const fetchMeeting = async () => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7071'
      const response = await fetch(`${baseUrl}/basicinfo/${meetingId}`)
      const data = await response.json()
      if (data.success && data.basicInfo) {
        setMeeting(data.basicInfo)
      }
    } catch (error) {
      console.error('Error fetching meeting:', error)
    }
  }

  const fetchSegments = async () => {
    try {
      setLoading(true)
      const segments = await getConversationSegments(meetingId)
      setSegments(segments)
      
      // セグメントごとにコメントを取得
      for (const segment of segments) {
        fetchCommentsBySegmentId(segment.segment_id)
      }
      
      setLoading(false)
    } catch (error) {
      console.error('Error fetching segments:', error)
      setLoading(false)
    }
  }

  const fetchCommentsBySegmentId = async (segmentId: number) => {
    try {
      const commentList = await getComments(segmentId)
      setComments(prev => ({
        ...prev,
        [segmentId]: commentList
      }))
      
      // 未読コメントを既読にする処理を一時的に無効化
      /*
      commentList.forEach((comment: Comment) => {
        const isRead = comment.readers.some(reader => reader.reader_id === userId)
        if (!isRead) {
          markAsRead(comment.comment_id, userId)
        }
      })
      */
    } catch (error) {
      console.error(`Error fetching comments for segment ${segmentId}:`, error)
    }
  }

  const handleCommentChange = (segmentId: number, content: string) => {
    setNewComments(prev => ({
      ...prev,
      [segmentId]: content
    }))
  }

  const handleAddComment = async (segmentId: number) => {
    const content = newComments[segmentId]
    if (!content || content.trim() === '') return

    setSubmitting(true)
    console.log("[コメント送信] 開始", { segmentId, meetingId, userId, content })

    try {
      console.log("[コメント送信] API呼び出し直前")
      await apiAddComment(segmentId, parseInt(meetingId), content, userId)
      console.log("[コメント送信] API成功")

      fetchCommentsBySegmentId(segmentId)
      document.getElementById(`comments-list-${segmentId}`)?.classList.remove('hidden')
      setNewComments(prev => ({ ...prev, [segmentId]: '' }))
    } catch (error) {
      console.error("[コメント送信] エラー", error)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteComment = async (commentId: number, segmentId: number) => {
    try {
      console.log("[コメント削除] 開始", { commentId, segmentId })
      
      // 削除確認ダイアログ
      if (!window.confirm('このコメントを削除してもよろしいですか？')) {
        console.log("[コメント削除] キャンセル")
        return
      }
      
      const response = await deleteComment(commentId)
      
      if (!response.success) {
        throw new Error(response.message || 'コメントの削除に失敗しました')
      }
      
      console.log("[コメント削除] 成功")
      
      // コメントリストを更新
      await fetchCommentsBySegmentId(segmentId)
      
      // 成功メッセージを表示（オプション）
      alert('コメントを削除しました')
      
    } catch (error) {
      console.error("[コメント削除] エラー", error)
      alert(error instanceof Error ? error.message : 'コメントの削除に失敗しました')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  const formatTime = (dateString: string) => {
    try {
      if (!dateString) return ''
      
      // ISO形式（末尾がZ）のUTC時間を処理
      if (dateString.includes('T') && dateString.endsWith('Z')) {
        // 「T」で分割して日付部分と時間部分を取得
        const [datePart, timePart] = dateString.split('T')
        // 「Z」を除去して時間部分を取得
        const timeWithoutZ = timePart.substring(0, timePart.length - 1)
        // 時と分だけを抽出
        const [hours, minutes] = timeWithoutZ.split(':')
        
        return `${datePart} ${hours}:${minutes}`
      }
      
      // その他のT区切り形式
      if (dateString.includes('T')) {
        // 'T'で分割して日付部分と時間部分を取得
        const [datePart, timePart] = dateString.split('T')
        // 時間部分から時と分を抽出 (小数点以下や秒を除去)
        const timeComponents = timePart.split(':')
        return `${datePart} ${timeComponents[0]}:${timeComponents[1]}`
      }
      
      // 空白区切りの形式
      if (dateString.includes(' ')) {
        const [datePart, timePart] = dateString.split(' ')
        const timeComponents = timePart.split(':')
        return `${datePart} ${timeComponents[0]}:${timeComponents[1]}`
      }
      
      // 日付オブジェクトでパースできる場合（最終手段）
      const date = new Date(dateString)
      if (!isNaN(date.getTime())) {
        const year = date.getFullYear()
        const month = (date.getMonth() + 1).toString().padStart(2, '0')
        const day = date.getDate().toString().padStart(2, '0')
        const hours = date.getHours().toString().padStart(2, '0')
        const minutes = date.getMinutes().toString().padStart(2, '0')
        
        return `${year}-${month}-${day} ${hours}:${minutes}`
      }
      
      // 上記以外のフォーマットはそのまま返す
      return dateString
    } catch (error) {
      return dateString
    }
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-3xl">
      {meeting && (
        <div className="border border-gray-200 rounded-xl bg-slate-50 shadow-md overflow-hidden">
          <div className="p-3 border-b border-gray-200 bg-white">
            <div className="flex items-center gap-3">
              <Link 
                href="/dashboard" 
                className="text-gray-600 hover:text-primary transition-colors"
                title="ダッシュボードに戻る"
              >
                <ArrowLeft className="h-4 w-4" />
              </Link>
              <div>
                <h1 className="text-base font-bold">
                  商談：{meeting.client_company_name} 様
                  <span className="text-xs text-gray-600 font-normal ml-2">
                    {new Date(meeting.meeting_datetime).toLocaleDateString('ja-JP', { 
                      year: 'numeric', 
                      month: '2-digit', 
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </h1>
              </div>
            </div>
          </div>
          <div className="p-6">
            <style jsx global>{`
              .chat-bubble-left::before {
                content: "";
                position: absolute;
                left: -8px;
                top: 12px;
                width: 0;
                height: 0;
                border: 8px solid transparent;
                border-right-color: #dbeafe; /* bg-blue-100 */
              }
              .chat-bubble-right::before {
                content: "";
                position: absolute;
                right: -8px;
                top: 12px;
                width: 0;
                height: 0;
                border: 8px solid transparent;
                border-left-color: #bbf7d0; /* bg-green-100 */
              }
              /* カスタムスクロールバー */
              .custom-scrollbar::-webkit-scrollbar {
                width: 6px;
              }
              .custom-scrollbar::-webkit-scrollbar-track {
                background: transparent;
              }
              .custom-scrollbar::-webkit-scrollbar-thumb {
                background-color: #cbd5e1;
                border-radius: 3px;
              }
              .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                background-color: #94a3b8;
              }
            `}</style>
            
            <div className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto overflow-x-hidden custom-scrollbar">
              {!segments.length ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">会話データがありません</p>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {segments.map(segment => {
                    // サマリ表示（user_id === 0）
                    if (segment.user_id === 0) {
                      return (
                        <div key={segment.segment_id} className="my-1 text-center">
                          <div className="text-sm text-gray-700 bg-slate-50 rounded px-2 py-0.5 whitespace-pre-wrap leading-tight">
                            ──────────{segment.content}──────────
                          </div>
                        </div>
                      )
                    }

                    // 通常のふきだし表示（user_id !== 0）
                    const isSpeaker1 = segment.speaker_name === '1'
                    const isSpeaker2 = segment.speaker_name === '2'
                    const speakerName = segment.speaker_name || 'Unknown'
                    const commentCount = comments[segment.segment_id]?.length || 0
                    const displayContent = segment.content
                    
                    return (
                      <div key={segment.segment_id} className={`flex ${isSpeaker2 ? 'justify-start' : 'justify-end'}`}>
                        <div className={`max-w-[75%] flex flex-col ${isSpeaker2 ? 'items-start' : 'items-end'} break-words`}>
                          {/* メッセージ本体 */}
                          <div className={`relative px-3 py-1.5 rounded-2xl shadow-lg w-full ${
                            isSpeaker2 
                              ? 'bg-blue-100 rounded-tl-none chat-bubble-left' 
                              : 'bg-green-100 rounded-tr-none chat-bubble-right'
                          }`}>
                            <div className={`flex items-center gap-2 mb-0.5 ${
                              isSpeaker2 ? 'justify-start' : 'justify-end'
                            }`}>
                              <div className="font-medium text-sm">{speakerName}</div>
                              <span className="text-xs text-gray-500">
                                {segment.inserted_datetime && formatTime(segment.inserted_datetime)}
                              </span>
                            </div>
                            <p className="text-sm text-gray-800 whitespace-pre-wrap leading-tight">{displayContent}</p>
                          </div>

                          {/* コントロール部分 */}
                          <div className={`flex items-center gap-2 mt-0.5 ${isSpeaker2 ? 'justify-start' : 'justify-end'}`}>
                            <AudioSegmentPlayer
                              segmentId={segment.segment_id}
                              startTime={segment.start_time}
                              audioPath={segment.audio_path || ''}
                            />
                            <button 
                              className={`flex items-center gap-1 text-sm text-gray-500 hover:text-blue-600 transition-colors ${
                                commentCount > 0 ? 'font-medium' : ''
                              }`}
                              onClick={() => document.getElementById(`comments-list-${segment.segment_id}`)?.classList.toggle('hidden')}
                            >
                              <MessageCircle size={16} />
                              <span>コメント ({commentCount})</span>
                            </button>
                          </div>

                          {/* コメント一覧と入力フォーム */}
                          <div id={`comments-list-${segment.segment_id}`} className="mt-1 hidden w-full">
                            {comments[segment.segment_id]?.length > 0 ? (
                              <CommentList
                                comments={comments[segment.segment_id]}
                                onCommentRead={(commentId) => {
                                  // コメントの既読状態を更新
                                  setComments(prev => ({
                                    ...prev,
                                    [segment.segment_id]: prev[segment.segment_id].map(comment =>
                                      comment.comment_id === commentId
                                        ? {
                                            ...comment,
                                            readers: [
                                              ...comment.readers,
                                              { reader_id: userId, read_datetime: new Date().toISOString() }
                                            ]
                                          }
                                        : comment
                                    )
                                  }))
                                }}
                                onDeleteComment={(commentId) => handleDeleteComment(commentId, segment.segment_id)}
                              />
                            ) : <div className="text-sm text-gray-500 mb-2">まだコメントはありません</div>}
                            
                            {/* コメント入力フォーム */}
                            <div className="flex gap-2">
                              <input
                                type="text"
                                className="flex-1 px-2 py-1 border rounded-md text-sm"
                                placeholder="コメントを入力..."
                                value={newComments[segment.segment_id] || ''}
                                onChange={(e) => handleCommentChange(segment.segment_id, e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && !submitting && handleAddComment(segment.segment_id)}
                                disabled={submitting}
                              />
                              <button
                                disabled={submitting}
                                className={`px-2 py-1 rounded-md text-sm transition-colors
                                  ${submitting ? 'bg-gray-300 cursor-not-allowed' : 'bg-primary text-white hover:bg-primary/90'}
                                `}
                                onClick={() => handleAddComment(segment.segment_id)}
                              >
                                {submitting ? '送信中…' : '送信'}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
            
            {/* 全体音声再生コントローラー */}
            {segments.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-200">
                <AudioController audioPath={segments[0].audio_path || ''} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}