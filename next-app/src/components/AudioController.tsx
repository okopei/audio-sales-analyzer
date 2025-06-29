'use client'

import { useRef, useState, useEffect } from 'react'
import { PlayIcon, PauseIcon } from '@heroicons/react/24/solid'

interface AudioControllerProps {
  audioPath: string
}

export const AudioController: React.FC<AudioControllerProps> = ({ audioPath }) => {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const updateTime = () => {
      setCurrentTime(audio.currentTime)
    }
    
    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)
    const handleEnded = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', updateTime)
    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.removeEventListener('timeupdate', updateTime)
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      audio.removeEventListener('ended', handleEnded)
    }
  }, [])

  const handlePlayPause = async () => {
    const audio = audioRef.current
    if (!audio) return
    
    try {
      if (isPlaying) {
        audio.pause()
      } else {
        await audio.play()
      }
    } catch (error) {
      console.error('再生エラー:', error)
      setError('音声の再生に失敗しました')
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = Number(e.target.value)
    if (audioRef.current && !isNaN(time)) {
      audioRef.current.currentTime = time
      setCurrentTime(time) // 即座にUIを更新
    }
  }

  // 時間を mm:ss 形式にフォーマットする関数
  const formatTime = (seconds: number): string => {
    if (isNaN(seconds) || seconds === 0) return '00:00'
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-md shadow-sm w-full max-w-xl">
      <button 
        onClick={handlePlayPause}
        className="p-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-full flex-shrink-0"
        disabled={!!error}
      >
        {isPlaying ? <PauseIcon className="w-4 h-4" /> : <PlayIcon className="w-4 h-4" />}
      </button>
      <input
        type="range"
        min={0}
        max={duration || 0}
        value={currentTime || 0}
        onChange={handleSeek}
        className="flex-1"
        disabled={!!error || duration === 0}
        step="0.1"
      />
      <div className="text-xs text-gray-600 font-mono whitespace-nowrap flex-shrink-0">
        {formatTime(currentTime)} / {formatTime(duration)}
      </div>
      <audio
        ref={audioRef}
        src={audioPath}
        onLoadedMetadata={() => {
          if (audioRef.current) {
            setDuration(audioRef.current.duration)
            setCurrentTime(0)
          }
        }}
        onError={(e) => {
          const audioElement = e.currentTarget as HTMLAudioElement
          if (process.env.NODE_ENV === 'development') {
            console.error('音声ファイルエラー:', {
              code: audioElement.error?.code,
              message: audioElement.error?.message,
              state: `network:${audioElement.networkState}, ready:${audioElement.readyState}`
            })
          }
          setError(`音声ファイルの読み込みに失敗しました: ${audioElement.error?.message || '不明なエラー'}`)
        }}
      />
      {error && (
        <div className="text-red-500 text-sm">
          {error}
        </div>
      )}
    </div>
  )
}

export default AudioController 