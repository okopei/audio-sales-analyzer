'use client'

import { useState, useRef, useEffect } from 'react'
import { BlockBlobClient } from '@azure/storage-blob'
import { useRouter } from 'next/navigation'

interface TranscriptionResponse {
  status: string
  original_text?: string
  error?: string
  steps?: {
    file_received: boolean
    speech_recognition_completed: boolean
  }
}

interface UploadResponse {
  success: boolean
  url?: string
  error?: string
}

export const useRecording = () => {
  const router = useRouter()
  const [isRecording, setIsRecording] = useState(false)
  const [transcription, setTranscription] = useState<TranscriptionResponse | null>(null)
  const [processingStatus, setProcessingStatus] = useState('')
  const [uploadStatus, setUploadStatus] = useState<UploadResponse | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [hasUploaded, setHasUploaded] = useState(false) // 一度だけアップロードするためのフラグ
  const [hasNavigated, setHasNavigated] = useState(false) // 一度だけ遷移するためのフラグ
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const [isPaused, setIsPaused] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null)
  const recordingBlobRef = useRef<Blob | null>(null) // 直接参照するためのRef
  // 音声レベル検出用の状態と参照
  const [audioLevel, setAudioLevel] = useState<number[]>(Array(50).fill(0))
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const audioDataRef = useRef<Uint8Array | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)

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

  // 音声レベルを更新する関数
  const updateAudioLevel = () => {
    if (!analyserRef.current || !audioDataRef.current) return
    
    analyserRef.current.getByteFrequencyData(audioDataRef.current)
    
    // 音声データから平均レベルを計算
    const average = audioDataRef.current.reduce((sum, value) => sum + value, 0) / audioDataRef.current.length
    
    // 新しい配列を作成（古い値をシフトして新しい値を追加）
    setAudioLevel(prev => {
      const newLevels = [...prev.slice(1), Math.min(100, average)]
      return newLevels
    })
    
    // アニメーションフレームを継続
    animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
  }

  // コンポーネントのアンマウント時にリソースを解放
  useEffect(() => {
    return () => {
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close()
      }
      
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  // Blob保存用のヘルパー関数
  const saveRecordingBlob = (blob: Blob) => {
    console.log(`saveRecordingBlob: 保存するBlob - サイズ=${blob.size}, type=${blob.type}`);
    
    // 両方に保存して確実にキャプチャする
    setRecordingBlob(blob);
    recordingBlobRef.current = blob;
  };

  const startRecording = async () => {
    try {
      // リセット
      setRecordingBlob(null);
      recordingBlobRef.current = null;
      chunksRef.current = [];
      setHasUploaded(false); // アップロードフラグをリセット
      setHasNavigated(false); // 遷移フラグをリセット
      
      console.log("録音を開始します: 初期化完了");
      
      // すでに使用中のメディアストリームがあれば停止
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
      }
      
      // AudioContextが既に存在する場合は閉じる
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close()
      }
      
      // 新しいメディアストリームを取得
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      })
      
      mediaStreamRef.current = stream
      
      // AudioContextとAnalyserNodeをセットアップ
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 256
      
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      
      // FFTデータ配列を作成
      const bufferLength = analyserRef.current.frequencyBinCount
      audioDataRef.current = new Uint8Array(bufferLength)
      
      // 音声レベル監視を開始
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
      
      // MediaRecorderのオプション
      const options: MediaRecorderOptions = {
        audioBitsPerSecond: 128000, // 音質を指定（128kbps）
        mimeType: 'audio/webm'
      }
      
      // メディアレコーダーを初期化
      console.log("MediaRecorderを初期化します:", options);
      const mediaRecorder = new MediaRecorder(stream, options);
      
      mediaRecorderRef.current = mediaRecorder
      
      // データチャンク追加ログ用のカウンター
      let chunkCounter = 0
      
      mediaRecorder.ondataavailable = (e) => {
        console.log(`データ利用可能イベント発生: サイズ=${e.data.size}, type=${e.data.type}`);
        if (e.data.size > 0) {
          // 10チャンクごとに1回だけログを出力
          chunkCounter++
          if (chunkCounter % 5 === 0 || chunkCounter === 1) {
            console.log(`録音データ追加: ${chunkCounter}個目, ${e.data.size} bytes, type: ${e.data.type}`)
          }
          chunksRef.current.push(e.data)
          
          // 必要に応じて途中経過のBlobを作成（長時間録音時の保険）
          if (chunkCounter % 10 === 0) {
            try {
              // 実際のMIMEタイプを取得
              const mimeType = mediaRecorder.mimeType || 'audio/webm';
              const tempBlob = new Blob(chunksRef.current, { type: mimeType });
              console.log(`途中経過のBlob生成: ${tempBlob.size} bytes, type: ${mimeType}`);
              // 状態は更新せず、参照のみ保持
              recordingBlobRef.current = tempBlob;
            } catch (error) {
              console.error("途中経過のBlob生成エラー:", error);
            }
          }
        }
      }

      mediaRecorder.onstop = () => {
        console.log("MediaRecorder.onstopイベントが発生しました");
        // 録音停止時に録音データをBlobとして保存
        if (chunksRef.current.length > 0) {
          console.log(`録音停止: ${chunksRef.current.length}個のデータチャンク`)
          const totalSize = chunksRef.current.reduce((acc, chunk) => acc + chunk.size, 0)
          console.log(`録音データ合計サイズ: ${totalSize} bytes`)
          
          try {
            const mimeType = mediaRecorder.mimeType || 'audio/webm';
            console.log(`Blob生成開始: mimeType=${mimeType}, チャンク数=${chunksRef.current.length}`);
            
            // チャンクの詳細をログ出力
            chunksRef.current.slice(0, 3).forEach((chunk, i) => {
              console.log(`チャンク${i}: サイズ=${chunk.size}, type=${chunk.type}`);
            });
            
            const blob = new Blob(chunksRef.current, { type: mimeType });
            console.log(`Blob生成完了: ${blob.size} bytes, type: ${blob.type}`);
            
            // 両方に保存
            saveRecordingBlob(blob);
          } catch (error) {
            console.error("Blob生成中にエラーが発生しました:", error);
          }
        } else {
          console.warn('録音データがありません')
        }
        
        // 音声レベル監視を停止
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
          animationFrameRef.current = null
        }
      }

      // エラーハンドリング
      mediaRecorder.onerror = (event) => {
        console.error("MediaRecorderでエラーが発生しました:", event);
      };

      startTimer()
      // より小さなタイムスライスに設定して頻繁にデータを取得
      mediaRecorder.start(500)
      console.log("録音を開始しました");
      setIsRecording(true)
    } catch (error) {
      console.error('録音開始エラー:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      console.log("録音を停止します");
      
      // 追加：もし既に録音データがある場合は保持する
      if (chunksRef.current.length > 0) {
        console.log("録音停止直前のデータ確認:", { 
          chunksLength: chunksRef.current.length,
          totalSize: chunksRef.current.reduce((acc, chunk) => acc + chunk.size, 0)
        })
        
        try {
          // recordingBlobをすぐに作成（ステート更新の前に）
          const mimeType = mediaRecorderRef.current.mimeType || 'audio/webm';
          const blob = new Blob(chunksRef.current, { type: mimeType })
          console.log("stopRecording内でBlob生成:", {
            size: blob.size,
            type: blob.type
          })
          
          // 両方に保存
          saveRecordingBlob(blob);
        } catch (error) {
          console.error("stopRecording内のBlob生成エラー:", error);
        }
      } else {
        console.warn("録音停止時にチャンクデータがありません");
      }
      
      // MediaRecorderの停止
      try {
        mediaRecorderRef.current.stop()
        console.log("MediaRecorder.stop()が正常に呼び出されました");
      } catch (error) {
        console.error("MediaRecorder.stop()エラー:", error);
      }
      
      // タイマーとUIの更新
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      setIsRecording(false)
      setRecordingTime(0)
      
      // 音声レベル監視を停止
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
        animationFrameRef.current = null
      }
      
      // メディアストリームのトラックを停止
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }

  const getRecordingBlob = (): Blob | null => {
    console.log("getRecordingBlob呼び出し:", {
      hasChunks: chunksRef.current.length > 0,
      hasRecordingBlob: !!recordingBlob,
      hasRecordingBlobRef: !!recordingBlobRef.current,
    });
    
    // 優先順位: 1. refのBlob, 2. stateのBlob, 3. チャンクから新規作成
    if (recordingBlobRef.current) {
      return recordingBlobRef.current;
    }
    
    if (recordingBlob) {
      return recordingBlob;
    }
    
    if (chunksRef.current.length > 0) {
      try {
        // 実際のMIMEタイプを取得
        const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        console.log(`チャンクから新規Blob生成: ${blob.size} bytes, type: ${mimeType}`);
        // 作成したBlobを保存しておく
        saveRecordingBlob(blob);
        return blob;
      } catch (error) {
        console.error("getRecordingBlob内のBlob生成エラー:", error);
      }
    }
    
    return null;
  }

  const getRecordingData = (): Blob | null => {
    // より確実に録音データを取得するために機能強化
    return getRecordingBlob();
  }

  // 追加: 現在の音声レベルを取得するテスト関数
  const testMicrophone = async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // テスト成功後にストリームを停止
      stream.getTracks().forEach(track => track.stop())
      return true
    } catch (error) {
      console.error("マイクのテストに失敗しました:", error)
      return false
    }
  }

  const sendAudioToServer = async (audioBlob: Blob, meetingId?: string, userId?: string): Promise<UploadResponse> => {
    try {
      console.log('🔵 アップロード開始:', {
        blobSize: audioBlob.size,
        blobType: audioBlob.type,
        timestamp: new Date().toISOString(),
        meetingId,
        userId,
        hasMeetingId: !!meetingId,
        hasUserId: !!userId
      })
      
      setIsUploading(true)
      setProcessingStatus(`音声データをアップロード中... (形式: ${audioBlob.type}, サイズ: ${(audioBlob.size / 1024 / 1024).toFixed(2)}MB)`)
      
      // ファイル名生成の共通関数
      const formatTimestamp = (date: Date): string => {
        return date.toISOString().replace(/:/g, '-').replace(/\..+/, match =>
          `-${match.slice(1, -1)}`
        )
      }
      
      const generateFileName = (meetingId: string | undefined, userId: string | undefined, extension: string = '.webm'): string => {
        const timestamp = formatTimestamp(new Date())
        
        if (meetingId && userId) {
          return `meeting_${meetingId}_user_${userId}_${timestamp}${extension}`
        } else if (userId) {
          return `recording_user_${userId}_${timestamp}${extension}`
        } else {
          return `recording_${timestamp}${extension}`
        }
      }
      
      // ファイル名を決定
      const fileName = generateFileName(meetingId, userId, '.webm')
      console.log('📁 生成されたファイル名:', {
        fileName,
        meetingId,
        userId,
        timestamp: formatTimestamp(new Date())
      })
      const file = new File([audioBlob], fileName, { type: 'audio/webm' })
      
      console.log('📁 ファイル作成:', {
        fileName,
        fileSize: file.size,
        fileType: file.type
      })
      
      // SASトークンを取得
      console.log('🔑 SASトークン取得開始')
      const sasResponse = await fetch(`/api/azure/get-sas-token?fileName=${encodeURIComponent(fileName)}`)
      
      if (!sasResponse.ok) {
        const errorText = await sasResponse.text()
        console.error('❌ SASトークン取得エラー:', {
          status: sasResponse.status,
          errorText
        })
        throw new Error(`SASトークンの取得に失敗しました: ${sasResponse.status} ${errorText}`)
      }
      
      const { sasUrl } = await sasResponse.json()
      console.log('✅ SAS URL取得成功:', sasUrl.split('?')[0]) // セキュリティのためSASトークン部分は省略
      
      // BlockBlobClientを使用して直接アップロード
      console.log('📤 Azure Storage直接アップロード開始')
      const blobClient = new BlockBlobClient(sasUrl)
      
      await blobClient.uploadData(file, {
        blobHTTPHeaders: {
          blobContentType: file.type
        }
      })
      
      console.log('✅ アップロード成功')
      
      setProcessingStatus('アップロード完了')
      setUploadStatus({ success: true, url: sasUrl.split('?')[0] }) // SASトークンなしのURLを返す
      
      // アップロード成功後、2秒後にダッシュボードに自動遷移
      setTimeout(() => {
        if (!hasNavigated) {
          console.log('🔄 ダッシュボードに自動遷移')
          setHasNavigated(true)
          router.push('/dashboard')
        }
      }, 2000)
      
      return { success: true, url: sasUrl.split('?')[0] }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'アップロードに失敗しました'
      console.error('❌ Error uploading audio:', error)
      setProcessingStatus('アップロードに失敗しました')
      setUploadStatus({ success: false, error: errorMessage })
      
      return { success: false, error: errorMessage }
    } finally {
      setIsUploading(false)
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

  // 録音停止時の自動アップロード処理
  useEffect(() => {
    if (!isRecording && recordingBlob && !isUploading && !hasUploaded) {
      console.log('🔄 録音停止を検知、自動アップロードを開始')
      console.log('📊 アップロード条件確認:', {
        isRecording,
        hasRecordingBlob: !!recordingBlob,
        isUploading,
        hasUploaded
      })
      
      // URLパラメータからmeetingIdとuserIdを取得
      const urlParams = new URLSearchParams(window.location.search)
      const meetingId = urlParams.get('meetingId')
      const userId = urlParams.get('userId')
      
      console.log('🔍 自動アップロード時のパラメータ:', {
        meetingId,
        userId,
        hasMeetingId: !!meetingId,
        hasUserId: !!userId
      })
      
      // meetingIdとuserIdを渡してアップロード
      sendAudioToServer(recordingBlob, meetingId || undefined, userId || undefined)
      setHasUploaded(true) // 一度だけ実行するためのフラグ
    }
  }, [isRecording, recordingBlob, isUploading, hasUploaded])

  return {
    isRecording,
    transcription,
    processingStatus,
    uploadStatus,
    isUploading,
    hasUploaded,
    startRecording,
    stopRecording,
    isPaused,
    pauseRecording,
    resumeRecording,
    setIsRecording: updateRecordingState,
    recordingTime,
    formatTime,
    getRecordingBlob,
    getRecordingData,
    recordingBlob,
    audioLevel, // 音声レベルの配列を返す
    testMicrophone, // マイクテスト関数を追加
    sendAudioToServer // 手動アップロード用
  }
} 