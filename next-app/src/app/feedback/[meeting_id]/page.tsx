'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { getConversationSegments, getComments, addComment as apiAddComment, markAsRead } from '@/lib/api/feedback'
import { useAuth } from '@/hooks/useAuth'
import ChatMessage from '@/components/ChatMessage'
import AudioSegmentPlayer from '@/components/AudioSegmentPlayer'

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
  const [expandedSegments, setExpandedSegments] = useState<Record<number, boolean>>({})
  
  // ログインユーザーID（実際のユーザーIDまたはデフォルト値として1）
  const userId = user?.user_id || 1

  useEffect(() => {
    fetchMeeting()
    fetchSegments()
  }, [meetingId, userId])

  const fetchMeeting = async () => {
    try {
      const response = await fetch(`http://localhost:7071/api/basicinfo/${meetingId}`)
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

    try {
      await apiAddComment(segmentId, parseInt(meetingId), content, userId)
      
      // コメント追加成功後、コメントリストを更新
      fetchCommentsBySegmentId(segmentId)
      
      // コメント一覧を表示する
      document.getElementById(`comments-list-${segmentId}`)?.classList.remove('hidden')
      
      // 入力フィールドをクリア
      setNewComments(prev => ({
        ...prev,
        [segmentId]: ''
      }))
    } catch (error) {
      console.error('Error adding comment:', error)
    }
  }

  const toggleExpand = (segmentId: number) => {
    setExpandedSegments(prev => ({
      ...prev,
      [segmentId]: !prev[segmentId]
    }))
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
      <div className="mb-4">
        <Link href="/dashboard" className="flex items-center text-gray-600 hover:text-primary">
          <ArrowLeft className="mr-2 h-4 w-4" />
          <span>ダッシュボードに戻る</span>
        </Link>
      </div>

      {meeting && (
        <div className="mb-6">
          <h1 className="text-xl font-bold mb-1">商談：{meeting.client_company_name} 様</h1>
          <p className="text-gray-600">
            {new Date(meeting.meeting_datetime).toLocaleDateString('ja-JP', { 
              year: 'numeric', 
              month: '2-digit', 
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </p>
        </div>
      )}

      <div className="space-y-4 mt-6">
        {!segments.length ? (
          <div className="text-center py-8">
            <p className="text-gray-500">会話データがありません</p>
          </div>
        ) : (
          segments.map(segment => {
            const isCustomer = segment.speaker_role !== '営業担当';
            const speakerName = segment.speaker_name || (isCustomer ? 'お客様' : '営業担当');
            const commentCount = comments[segment.segment_id]?.length || 0;
            const isExpanded = expandedSegments[segment.segment_id];
            const isCurrentUser = segment.user_id === userId;
            const displayContent = segment.content;
            const shouldShowExpandButton = segment.content.length > 100;
            
            return (
              <div key={segment.segment_id} className="flex flex-col">
                <div className={`flex items-start ${isCurrentUser ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex-1 max-w-[80%] ${isCurrentUser ? 'ml-12' : 'mr-12'}`}>
                    {/* メッセージ本体 */}
                    <div className={`relative p-3 rounded-lg ${
                      isCurrentUser ? 'bg-blue-100' : isCustomer ? 'bg-green-50' : 'bg-blue-50'
                    }`}>
                      <div className="flex justify-between items-start mb-1">
                        <div className="font-semibold">{speakerName}</div>
                        <span className="text-xs text-gray-500 ml-2">
                          {segment.inserted_datetime && formatTime(segment.inserted_datetime)}
                        </span>
                      </div>
                      <p className="whitespace-pre-wrap text-sm">{displayContent}</p>
                      {shouldShowExpandButton && (
                        <button 
                          className="text-xs text-blue-600 mt-1 flex items-center gap-1"
                          onClick={() => toggleExpand(segment.segment_id)}
                        >
                          <span>全文を表示</span>
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
                            <polyline points="6 9 12 15 18 9"></polyline>
                          </svg>
                        </button>
                      )}
                    </div>

                    {/* コントロール部分（再生ボタンとコメントを横並びに） */}
                    <div className="flex items-center gap-2 mt-2">
                      <AudioSegmentPlayer
                        segmentId={segment.segment_id}
                        startTime={segment.start_time}
                        endTime={segment.end_time}
                        audioUrl={segment.file_path}
                      />
                      <button 
                        className={`text-xs flex items-center gap-1 px-2 py-1 rounded-full ${
                          commentCount > 0 
                            ? 'bg-blue-100 text-blue-700 font-medium hover:bg-blue-200' 
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                        onClick={() => document.getElementById(`comments-list-${segment.segment_id}`)?.classList.toggle('hidden')}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
                          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                        </svg>
                        <span>コメント ({commentCount})</span>
                      </button>
                    </div>

                    {/* コメント一覧と入力フォーム */}
                    <div id={`comments-list-${segment.segment_id}`} className={`pl-4 mb-4 hidden ${isCurrentUser ? 'text-right' : 'text-left'}`}>
                      {comments[segment.segment_id]?.length > 0 ? (
                        <div className="space-y-2 mb-3">
                          {comments[segment.segment_id].map(comment => (
                            <div key={comment.comment_id} className="bg-white p-2 rounded shadow-sm border border-gray-100 text-left">
                              <div className="flex justify-between items-start">
                                <span className="font-semibold text-xs">{comment.user_name}</span>
                                <span className="text-xs text-gray-500">{formatTime(comment.inserted_datetime)}</span>
                              </div>
                              <p className="text-sm mt-1">{comment.content}</p>
                            </div>
                          ))}
                        </div>
                      ) : <div className="text-sm text-gray-500 mb-3">まだコメントはありません</div>}
                      
                      {/* コメント入力フォーム */}
                      <div className="mt-3">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            className="flex-1 px-3 py-1 border rounded-md text-sm"
                            placeholder="コメントを入力..."
                            value={newComments[segment.segment_id] || ''}
                            onChange={(e) => handleCommentChange(segment.segment_id, e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleAddComment(segment.segment_id)}
                          />
                          <button
                            className="px-3 py-1 bg-primary text-white rounded-md text-sm hover:bg-primary/90 transition-colors"
                            onClick={() => handleAddComment(segment.segment_id)}
                          >
                            送信
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  )
} 