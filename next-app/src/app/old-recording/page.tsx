'use client'
import { useState, useRef } from 'react'

interface TranscriptionResponse {
  status: string;
  original_text?: string;
  error?: string;
  steps?: {
    file_received: boolean;
    speech_recognition_completed: boolean;
  };
}

export default function Home() {
  const [isRecording, setIsRecording] = useState(false)
  const [transcription, setTranscription] = useState<TranscriptionResponse | null>(null)
  const [debugInfo, setDebugInfo] = useState('')
  const [processingStatus, setProcessingStatus] = useState('')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=pcm'
      })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
          setDebugInfo(prev => prev + `\nChunk received: ${e.data.size} bytes`)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { 
          type: 'audio/wav'
        })
        setDebugInfo(prev => prev + `\nRecording complete. Total size: ${audioBlob.size} bytes`)
        await sendAudioToServer(audioBlob)
      }

      mediaRecorder.start()
      setIsRecording(true)
      setDebugInfo('Recording started...')
    } catch (error) {
      console.error('Error accessing microphone:', error)
      setDebugInfo(`Error: ${error}`)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setDebugInfo(prev => prev + '\nStopping recording...')
    }
  }

  const sendAudioToServer = async (audioBlob: Blob) => {
    try {
      setProcessingStatus('音声データを送信中...')
      const formData = new FormData()
      formData.append('audio', audioBlob)
      setDebugInfo(prev => prev + '\nSending to server...')

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
      
      setDebugInfo(prev => prev + '\nServer response received')
    } catch (error) {
      setProcessingStatus('エラーが発生しました')
      console.error('Error sending audio:', error)
      setDebugInfo(prev => prev + `\nError sending to server: ${error}`)
    }
  }

  return (
    <div className="flex flex-col items-center gap-4 p-8">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        className="px-4 py-2 bg-blue-500 text-white rounded"
      >
        {isRecording ? '録音停止' : '録音開始'}
      </button>
      
      {processingStatus && (
        <div className="mt-4 w-full max-w-lg">
          <h3 className="font-bold">処理状況:</h3>
          <div className="mt-2 p-3 bg-blue-50 rounded">
            <p>{processingStatus}</p>
            {transcription?.steps && (
              <ul className="mt-2 space-y-1">
                <li>✓ ファイル受信: {transcription.steps.file_received ? '完了' : '処理中'}</li>
                <li>✓ 音声認識: {transcription.steps.speech_recognition_completed ? '完了' : '処理中'}</li>
              </ul>
            )}
          </div>
        </div>
      )}
      
      {transcription?.status === 'success' && (
        <div className="mt-4 w-full max-w-lg">
          <div className="mb-4">
            <h3 className="font-bold">文字起こし結果:</h3>
            <p className="mt-2 p-3 bg-gray-50 rounded">{transcription.original_text}</p>
          </div>
        </div>
      )}

      <div className="mt-4 p-4 bg-gray-100 rounded-lg w-full max-w-lg">
        <h3 className="font-bold mb-2">デバッグ情報:</h3>
        <pre className="whitespace-pre-wrap text-sm">
          {debugInfo}
        </pre>
      </div>
    </div>
  )
}
