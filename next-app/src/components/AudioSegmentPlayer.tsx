'use client'

import { PlayIcon, StopIcon } from '@heroicons/react/24/solid'
import { useState, useRef, useEffect } from 'react'

interface AudioSegmentPlayerProps {
  segmentId: number
  startTime: number
  endTime: number
  audioUrl: string
}

const AudioSegmentPlayer = ({ segmentId, startTime, endTime, audioUrl }: AudioSegmentPlayerProps) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (!audioRef.current) return

    const stopAtEnd = () => {
      if (audioRef.current?.currentTime >= endTime) {
        audioRef.current.pause()
        setIsPlaying(false)
      }
    }

    audioRef.current.addEventListener('timeupdate', stopAtEnd)
    return () => audioRef.current?.removeEventListener('timeupdate', stopAtEnd)
  }, [endTime])

  const handlePlayClick = () => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.currentTime = startTime
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handlePlayClick}
        className="p-2 rounded-full hover:bg-gray-100 transition-colors"
        aria-label={isPlaying ? '停止' : '再生'}
      >
        {isPlaying ? (
          <StopIcon className="w-5 h-5 text-gray-600" />
        ) : (
          <PlayIcon className="w-5 h-5 text-gray-600" />
        )}
      </button>
      <audio 
        ref={audioRef} 
        src={audioUrl}
        onError={(e) => console.error('音声再生エラー:', e)} 
      />
    </div>
  )
}

export default AudioSegmentPlayer 