'use client'

import { useState, useRef } from 'react'

interface TranscriptionResponse {
  status: string
  original_text?: string
  error?: string
  steps?: {
    file_received: boolean
    speech_recognition_completed: boolean
  }
}

export const useRecording = () => {
  const [isRecording, setIsRecording] = useState(false)
  const [transcription, setTranscription] = useState<TranscriptionResponse | null>(null)
  const [processingStatus, setProcessingStatus] = useState('')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const [isPaused, setIsPaused] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const startTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
    }
    timerRef.current = setInterval(() => {
      setRecordingTime(prev => prev + 1)
    }, 1000)
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=pcm'
      })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0 && !isPaused) {
          chunksRef.current.push(e.data)
        }
      }

      startTimer()
      mediaRecorder.start(100)
      setIsRecording(true)
    } catch (error) {
      console.error('Error:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop()
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      setIsRecording(false)
      setRecordingTime(0)
    }
  }

  const sendAudioToServer = async (audioBlob: Blob) => {
    try {
      setProcessingStatus('音声データを送信中...')
      const formData = new FormData()
      formData.append('audio', audioBlob)

      const response = await fetch('/api/transcribe', {
        method: 'POST',
        body: formData,
      })

      const data: TranscriptionResponse = await response.json()
      setTranscription(data)
      
      if (data.status === 'error') {
        setProcessingStatus(`エラーが発生しました: ${data.error}`)
      } else {
        setProcessingStatus('処理完了')
      }
    } catch (error) {
      setProcessingStatus('エラーが発生しました')
      console.error('Error sending audio:', error)
    }
  }

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      try {
        mediaRecorderRef.current.pause()
        if (timerRef.current) {
          clearInterval(timerRef.current)
          timerRef.current = null
        }
        setIsPaused(true)
      } catch (error) {
        console.error('Pause error:', error)
      }
    }
  }

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isPaused) {
      try {
        mediaRecorderRef.current.resume()
        startTimer()
        setIsPaused(false)
      } catch (error) {
        console.error('Resume error:', error)
      }
    }
  }

  const updateRecordingState = async (value: boolean) => {
    if (value && mediaRecorderRef.current) return
    if (!value && !mediaRecorderRef.current) return

    if (value && !mediaRecorderRef.current) {
      await startRecording()
    } else if (!value && mediaRecorderRef.current) {
      stopRecording()
    }
  }

  return {
    isRecording,
    transcription,
    processingStatus,
    startRecording,
    stopRecording,
    isPaused,
    pauseRecording,
    resumeRecording,
    setIsRecording: updateRecordingState,
    recordingTime,
    formatTime,
  }
} 