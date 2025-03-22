'use client'

import { useState, useRef, useEffect } from 'react'

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
      
      // 試行する順番でmimeTypeのリストを作成
      const mimeTypes = [
        'audio/webm',                // 一般的なWebM形式
        'audio/webm;codecs=pcm',     // PCMコーデック付きWebM
        'audio/webm;codecs=opus',    // Opusコーデック付きWebM（広く対応）
        'audio/ogg;codecs=opus',     // OggOpus（Firefoxが対応）
        'audio/mp4;codecs=mp4a.40.5' // AAC（Safariが対応）
      ];
      
      // サポートされているmimeTypeを見つける
      let mimeType = '';
      for (const type of mimeTypes) {
        if (MediaRecorder.isTypeSupported(type)) {
          mimeType = type;
          console.log(`サポートされているメディアタイプ: ${mimeType}`);
          break;
        }
      }
      
      // MediaRecorderのオプション
      const options: MediaRecorderOptions = {
        audioBitsPerSecond: 128000, // 音質を指定（128kbps）
      };
      
      if (mimeType) {
        options.mimeType = mimeType;
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
              const tempBlob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType || 'audio/webm' });
              console.log(`途中経過のBlob生成: ${tempBlob.size} bytes`);
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
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        console.log(`チャンクから新規Blob生成: ${blob.size} bytes`);
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
    getRecordingBlob,
    getRecordingData,
    recordingBlob,
    audioLevel, // 音声レベルの配列を返す
    testMicrophone // マイクテスト関数を追加
  }
} 