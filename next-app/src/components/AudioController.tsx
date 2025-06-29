'use client'

import { useRef, useState, useEffect, useMemo } from 'react'
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

  // オーディオファイルのURLを構築する関数
  const constructAudioUrl = (audioPath: string): string => {
    if (!audioPath) {
      throw new Error('Invalid audio path: path is empty')
    }

    const storageAccountName = process.env.NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME
    const containerName = process.env.NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME
    const sasToken = process.env.NEXT_PUBLIC_AZURE_STORAGE_SAS_TOKEN

    if (!storageAccountName || !containerName || !sasToken) {
      throw new Error('Missing required environment variables for Azure Storage')
    }

    // パスの正規化
    const normalizedPath = audioPath
      .replace(/^\/+/, '') // 先頭のスラッシュを削除
      .replace(/\/+/g, '/') // 連続するスラッシュを1つに
      .replace(new RegExp(`^${containerName}/`, 'i'), '') // コンテナ名が重複している場合は削除

    // URLの構築
    const baseUrl = `https://${storageAccountName}.blob.core.windows.net`
    const containerUrl = `${baseUrl}/${containerName}`
    const blobUrl = `${containerUrl}/${normalizedPath}`

    // SASトークンの処理
    const normalizedSasToken = sasToken.startsWith('?') ? sasToken : `?${sasToken}`

    const finalUrl = `${blobUrl}${normalizedSasToken}`

    return finalUrl
  }

  // オーディオファイルのURLを構築
  const audioUrl = useMemo(() => {
    try {
      return constructAudioUrl(audioPath)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to construct audio URL'
      if (process.env.NODE_ENV === 'development') {
        console.error('Audio URL construction error:', error)
      }
      setError(errorMessage)
      return ''
    }
  }, [audioPath])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const updateTime = () => setCurrentTime(audio.currentTime)
    audio.addEventListener('timeupdate', updateTime)

    return () => {
      audio.removeEventListener('timeupdate', updateTime)
    }
  }, [])

  const handlePlayPause = () => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.pause()
    } else {
      audio.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = Number(e.target.value)
    if (audioRef.current) {
      audioRef.current.currentTime = time
    }
  }

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-gray-100 rounded-md shadow-sm w-full max-w-xl">
      <button 
        onClick={handlePlayPause}
        className="p-2 bg-blue-500 hover:bg-blue-600 text-white rounded-full"
        disabled={!!error}
      >
        {isPlaying ? <PauseIcon className="w-5 h-5" /> : <PlayIcon className="w-5 h-5" />}
      </button>
      <input
        type="range"
        min={0}
        max={duration}
        value={currentTime}
        onChange={handleSeek}
        className="w-full"
        disabled={!!error}
      />
      <audio
        ref={audioRef}
        src={audioUrl}
        onLoadedMetadata={() => {
          if (audioRef.current) setDuration(audioRef.current.duration)
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