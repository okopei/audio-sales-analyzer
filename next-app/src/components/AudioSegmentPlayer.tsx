'use client'

import { PlayIcon, StopIcon } from '@heroicons/react/24/solid'
import { useState, useRef, useEffect, useMemo } from 'react'

interface AudioSegmentPlayerProps {
  segmentId: number
  audioPath: string
  startTime?: number
}

export const AudioSegmentPlayer: React.FC<AudioSegmentPlayerProps> = ({
  segmentId,
  audioPath,
  startTime,
}) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)
  const validStartTimeRef = useRef<number | null>(null)

  // 環境変数のチェックは開発環境でのみ実行
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const missingEnvVars = []
      if (!process.env.NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME) missingEnvVars.push('ACCOUNT_NAME')
      if (!process.env.NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME) missingEnvVars.push('CONTAINER_NAME')
      if (!process.env.NEXT_PUBLIC_AZURE_STORAGE_SAS_TOKEN) missingEnvVars.push('SAS_TOKEN')
      
      if (missingEnvVars.length > 0) {
        console.warn('Missing environment variables:', missingEnvVars.join(', '))
      }
    }
  }, [])

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

  // startTimeの値を検証して変換する関数
  const validateStartTime = (value: unknown): number => {
    if (value === undefined || value === null) {
      throw new Error('Invalid startTime: value is null or undefined')
    }

    let numericValue: number
    
    if (typeof value === 'number') {
      numericValue = value
    } else if (typeof value === 'string') {
      numericValue = parseFloat(value)
    } else {
      throw new Error(`Invalid startTime: type ${typeof value} is not supported`)
    }

    if (Number.isNaN(numericValue)) {
      throw new Error('Invalid startTime: value is NaN')
    }

    if (!Number.isFinite(numericValue)) {
      throw new Error('Invalid startTime: value is not finite')
    }

    if (numericValue < 0) {
      throw new Error('Invalid startTime: value is negative')
    }

    return numericValue
  }

  // メタデータ読み込み時の処理
  const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLAudioElement>) => {
    const audio = e.currentTarget
    setDuration(audio.duration)
    
    try {
      // startTimeが未定義の場合は0を設定
      const validTime = startTime === undefined ? 0 : validateStartTime(startTime)
      validStartTimeRef.current = validTime
      audio.currentTime = validTime
      setIsLoaded(true)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to set initial currentTime'
      if (process.env.NODE_ENV === 'development') {
        console.error('handleLoadedMetadata error:', error)
      }
      setError(errorMessage)
      setIsLoaded(false)
    }
  }

  const handlePlay = () => {
    if (!audioRef.current || !isLoaded) return

    try {
      if (process.env.NODE_ENV === 'development') {
        console.warn('Play attempt:', {
          startTime,
          validStartTime: validStartTimeRef.current,
          isLoaded,
          readyState: audioRef.current.readyState
        })
      }

      if (validStartTimeRef.current === null) {
        setError('再生開始時間が設定されていません')
        return
      }

      audioRef.current.play()
      setIsPlaying(true)
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        console.error('handlePlay error:', err)
      }
      const errorMessage = err instanceof Error ? err.message : '不明なエラー'
      setIsPlaying(false)
      setError(`音声再生に失敗しました: ${errorMessage}`)
    }
  }

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={isPlaying ? handlePause : handlePlay}
        className="p-1.5 rounded-full bg-blue-500 text-white hover:bg-blue-600 transition-colors"
        disabled={!isLoaded}
      >
        {isPlaying ? <StopIcon className="w-4 h-4" /> : <PlayIcon className="w-4 h-4" />}
      </button>
      <audio
        ref={audioRef}
        src={audioUrl}
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
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
          setIsLoaded(false)
        }}
      />
      {error && (
        <div className="text-red-500 text-sm mt-2">
          {error}
        </div>
      )}
    </div>
  )
}

export default AudioSegmentPlayer