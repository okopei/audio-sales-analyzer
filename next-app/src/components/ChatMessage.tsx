'use client'

import { type ConversationSegment } from '@/types'
import AudioSegmentPlayer from './AudioSegmentPlayer'

interface ChatMessageProps {
  segment: ConversationSegment
}

const ChatMessage = ({ segment }: ChatMessageProps) => {
  const isCustomer = segment.speaker_role === 'Cust'
  const isSales = segment.speaker_role === 'Sale'

  return (
    <div className={`flex gap-2 ${isCustomer ? 'justify-start' : 'justify-end'}`}>
      {/* 音声再生ボタン */}
      <div className={`flex-shrink-0 pt-4 ${isCustomer ? 'order-1' : 'order-2'}`}>
        <AudioSegmentPlayer
          segmentId={segment.segment_id}
          startTime={segment.start_time}
<<<<<<< HEAD
          audioPath={segment.file_path}
=======
          audioPath={segment.audio_path || ''}
>>>>>>> develop
        />
      </div>

      {/* チャットメッセージ本体 */}
      <div className={`flex-grow flex flex-col gap-2 p-4 rounded-2xl shadow-sm max-w-[80%] ${
        isCustomer 
          ? 'bg-green-100 rounded-tl-none order-2' 
          : 'bg-blue-100 rounded-tr-none order-1'
      }`}>
        <div className={`flex ${isCustomer ? 'justify-start' : 'justify-end'} items-center gap-2`}>
          <span className="text-sm text-gray-500">
            {new Date(segment.inserted_datetime).toLocaleTimeString()}
          </span>
          <span className="font-medium">{segment.speaker_name}</span>
        </div>
        <p className="whitespace-pre-wrap text-sm">{segment.content}</p>
        <div className={`flex ${isCustomer ? 'justify-start' : 'justify-end'}`}>
          <button className="text-xs text-gray-500 hover:text-gray-700">
            コメント ({segment.comments?.length || 0})
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatMessage 