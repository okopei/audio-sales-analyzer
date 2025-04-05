'use client'

import { type ConversationSegment } from '@/types'
import AudioSegmentPlayer from './AudioSegmentPlayer'

interface ChatMessageProps {
  segment: ConversationSegment
}

const ChatMessage = ({ segment }: ChatMessageProps) => {
  return (
    <div className="flex gap-2">
      {/* 音声再生ボタン */}
      <div className="flex-shrink-0 pt-4">
        <AudioSegmentPlayer
          segmentId={segment.segment_id}
          startTime={segment.start_time}
          endTime={segment.end_time}
          audioUrl={segment.file_path}
        />
      </div>

      {/* チャットメッセージ本体 */}
      <div className={`flex-grow flex flex-col gap-2 p-4 rounded-lg ${
        segment.speaker_role === 'SALES' ? 'bg-blue-50' : 'bg-green-50'
      }`}>
        <div className="flex justify-between items-center">
          <span className="font-semibold">{segment.speaker_name}</span>
          <span className="text-sm text-gray-500">
            {new Date(segment.inserted_datetime).toLocaleTimeString()}
          </span>
        </div>
        <p>{segment.content}</p>
        <div className="flex justify-end">
          <button className="text-sm text-gray-500">
            コメント ({segment.comments?.length || 0})
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatMessage 