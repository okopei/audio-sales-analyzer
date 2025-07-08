"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dot, Pause, Play, ArrowLeft, Mic, Building, User, Calendar } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"
import { useRecording } from "@/hooks/useRecording"
import { toast } from "sonner"
import { useEffect, useState, useRef, Suspense } from "react"
import Link from "next/link"
import { useAuth } from "@/hooks/useAuth"
import { uploadToAzureStorage } from "@/lib/utils/azure-storage"
import { updateMeetingWithRecording, getBasicInfo, checkApiHealth, searchBasicInfo } from "@/lib/api-client"

// 波形コンポーネント
const Waveform = ({ audioLevel }: { audioLevel: number[] }) => {
  return (
    <div className="flex items-end h-16 gap-[2px] bg-black/5 rounded-md p-2 mb-4 overflow-hidden">
      {audioLevel.map((level, i) => (
        <div
          key={i}
          className="w-full bg-blue-500"
          style={{
            height: `${Math.max(4, level)}%`,
            opacity: Math.min(1, level / 50 + 0.2),
          }}
        />
      ))}
    </div>
  )
}

// マイクテストコンポーネント
const MicrophoneTest = ({ onTestComplete }: { onTestComplete: (success: boolean) => void }) => {
  const [isTesting, setIsTesting] = useState(false)
  const { testMicrophone } = useRecording()

  const handleTest = async () => {
    setIsTesting(true)
    try {
      const success = await testMicrophone()
      onTestComplete(success)
      if (success) {
        toast.success("マイクの接続が正常に確認できました")
      } else {
        toast.error("マイクの接続に問題があります。設定を確認してください")
      }
    } catch (error) {
      console.error("マイクテストエラー:", error)
      toast.error("マイクテスト中にエラーが発生しました")
      onTestComplete(false)
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <Card className="mb-4">
      <CardHeader className="py-3">
        <CardTitle className="text-base flex items-center">
          <Mic className="w-4 h-4 mr-2" />
          マイク接続テスト
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm mb-4">録音を開始する前に、マイクが正しく接続されているか確認してください。</p>
        <Button
          onClick={handleTest}
          disabled={isTesting}
          className="w-full"
        >
          {isTesting ? "テスト中..." : "マイクをテスト"}
        </Button>
      </CardContent>
    </Card>
  )
}

// 基本情報表示コンポーネント
interface BasicInfoDisplayProps {
  clientCompanyName: string
  clientContactName: string
  meetingDatetime: string
}

const BasicInfoDisplay = ({ clientCompanyName, clientContactName, meetingDatetime }: BasicInfoDisplayProps) => {
  // 日時をフォーマット
  const formatDate = (dateString: string) => {
    if (!dateString) return "日時未設定";
    
    try {
      const date = new Date(dateString);
      return date.toLocaleString('ja-JP', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch (e) {
      return dateString;
    }
  };
  
  return (
    <Card className="mb-4 border-blue-100 bg-gradient-to-r from-blue-50 to-white">
      <CardHeader className="py-3 border-b border-blue-100">
        <CardTitle className="text-base text-blue-800">商談情報</CardTitle>
      </CardHeader>
      <CardContent className="py-3">
        <div className="grid gap-3">
          <div className="flex items-center gap-2">
            <Building className="h-5 w-5 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">会社名:</span>
            <span className="text-sm font-semibold">{clientCompanyName || "未設定"}</span>
          </div>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">担当者名:</span>
            <span className="text-sm font-semibold">{clientContactName || "未設定"}</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">日時:</span>
            <span className="text-sm font-semibold">{formatDate(meetingDatetime)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// 型定義追加
interface BasicInfoData {
  client_company_name: string
  client_contact_name: string
  meeting_datetime: string
}

// useSearchParamsを使用するコンポーネント
function RecordingPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const meetingId = searchParams.get('meetingId')
  const { user } = useAuth()
  const [isUploading, setIsUploading] = useState(false)
  const [micTested, setMicTested] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [apiConnected, setApiConnected] = useState(false)
  const [basicInfo, setBasicInfo] = useState<{
    client_company_name: string;
    client_contact_name: string;
    meeting_datetime: string;
  } | null>(null)
  
  // 録音データを保持するための状態
  const [localRecordingBlob, setLocalRecordingBlob] = useState<Blob | null>(null)
  
  // useRecordingフックから必要な値を取得
  const {
    isRecording,
    setIsRecording,
    isPaused,
    recordingTime,
    processingStatus,
    pauseRecording,
    resumeRecording,
    startRecording,
    stopRecording,
    formatTime,
    recordingBlob,
    getRecordingBlob,
    audioLevel // 音声レベルデータを取得
  } = useRecording()

  // マイクテスト完了時のハンドラ
  const handleMicTestComplete = (success: boolean) => {
    setMicTested(success)
    if (success && !isRecording) {
      // マイクテスト成功後に自動的に録音を開始するオプション
      // setIsRecording(true)
    }
  }

  // APIサーバーの接続状態を確認
  useEffect(() => {
    const checkApiServer = async () => {
      try {
        console.log('APIサーバーの接続状態を確認中...');
        setIsLoading(true); // ローディング状態を有効化
        const healthResult = await checkApiHealth();
        console.log('API健康状態:', healthResult);
        
        setApiConnected(healthResult.status === 'ok');
        if (healthResult.status === 'ok') {
          console.log('APIサーバーに接続できました');
          toast.success('APIサーバーに接続しました');
          
          // URLパラメータまたはローカルストレージから基本情報を取得
          const hasUrlParams = !!meetingId;
          const hasStoredInfo = !!localStorage.getItem('basicMeetingInfo');
          
          console.log('情報取得方法:', { 
            URLパラメータあり: hasUrlParams, 
            ローカルストレージあり: hasStoredInfo 
          });
          
          // ユーザー情報が取得できていることを確認
          if (user) {
            // ユーザーIDを数値に変換
            const userIdNum = parseInt(user.user_id.toString(), 10);
            
            if (isNaN(userIdNum)) {
              console.error('ユーザーIDの形式が不正です:', user.user_id);
              toast.error("ユーザーIDの形式が不正です");
              setIsLoading(false);
              return;
            }
            
            // URLパラメータからmeetingIdを取得した場合
            if (hasUrlParams) {
              console.log('URLから取得した会議ID:', meetingId);
              const meetingIdNum = parseInt(meetingId, 10);
              
              if (!isNaN(meetingIdNum)) {
                // 数値に変換できた場合、会議IDで基本情報を取得
                fetchBasicInfo(meetingIdNum, userIdNum);
              } else {
                console.error('会議IDの形式が不正です:', meetingId);
                toast.error("会議IDの形式が不正です");
                setIsLoading(false);
              }
            } 
            // ローカルストレージから基本情報を取得する場合
            else if (hasStoredInfo) {
              console.log('ローカルストレージから基本情報を取得します');
              // nullを渡して、ローカルストレージの情報を使用
              fetchBasicInfo(null, userIdNum);
            } else {
              console.log('会議情報が取得できません。新規登録画面に戻ります。');
              toast.error('会議情報が見つかりません。新規登録画面に戻ります。');
              setIsLoading(false);
              
              // 新規登録画面に戻る
              setTimeout(() => {
                router.push('/newmeeting');
              }, 2000);
            }
          } else {
            console.log('ユーザー情報が取得できません');
            setIsLoading(false);
            toast.error('ユーザー情報が取得できません。ログイン画面に戻ります。');
            
            // ログイン画面に戻る
            setTimeout(() => {
              router.push('/');
            }, 2000);
          }
        } else {
          console.error('APIサーバーに接続できません:', healthResult);
          toast.error('APIサーバーに接続できません');
          setIsLoading(false);
        }
      } catch (error) {
        console.error('API health check failed:', error);
        setApiConnected(false);
        toast.error('APIサーバーに接続できません。Azure Functions が起動しているか確認してください。');
        setIsLoading(false);
      }
    };
    
    checkApiServer();
  }, [user, meetingId, router]);

  // 基本情報を取得する関数
  const fetchBasicInfo = async (meetingIdNum: number | null, userId: number) => {
    try {
      console.log(`基本情報を取得中... meeting ID: ${meetingIdNum}, user ID: ${userId}`);
      setIsLoading(true);
      
      // ローカルストレージから☆の情報を取得（会社名、担当者名、会議日時）
      let storedInfo = null;
      try {
        const storedInfoJson = localStorage.getItem('basicMeetingInfo');
        if (storedInfoJson) {
          storedInfo = JSON.parse(storedInfoJson);
          console.log('ローカルストレージから基本情報を取得:', storedInfo);
        }
      } catch (e) {
        console.warn('ローカルストレージからの情報取得に失敗:', e);
      }
      
      let response;
      
      // 会議IDが直接指定されている場合は通常の検索
      if (meetingIdNum) {
        console.log(`会議ID ${meetingIdNum} で基本情報を検索`);
        response = await getBasicInfo(meetingIdNum, userId);
      } 
      // ☆の情報がある場合は詳細検索
      else if (storedInfo && storedInfo.client_company_name && storedInfo.client_contact_name) {
        console.log('基本情報を詳細検索:', storedInfo);
        
        // ローカルストレージに保存されたユーザーIDがあればそれを使用、なければ現在のユーザーIDを使用
        const searchUserId = storedInfo.userId || userId;
        
        // searchBasicInfo関数を使用して、会社名、担当者名、会議日時に基づいて検索
        response = await searchBasicInfo(
          searchUserId,
          storedInfo.client_company_name,
          storedInfo.client_contact_name,
          storedInfo.meeting_datetime
        );
      } else {
        throw new Error('会議IDまたは基本情報が提供されていません');
      }
      
      console.log('Basic info API response:', response);
      
      // 基本情報が見つかるかどうかのチェック
      if (response.found && response.basic_info) {
        // 基本情報を設定
        const basicInfoData = {
          client_company_name: response.basic_info.client_company_name || '',
          client_contact_name: response.basic_info.client_contact_name || '',
          meeting_datetime: response.basic_info.meeting_datetime || '',
        };
        
        setBasicInfo(basicInfoData);
        
        // 基本情報をローカルストレージに保存（再読み込み時に使用）
        try {
          localStorage.setItem('basicMeetingInfo', JSON.stringify(basicInfoData));
        } catch (e) {
          console.warn('ローカルストレージへの保存に失敗しました', e);
        }
        
        // 基本情報の取得に成功した場合
        console.log('基本情報の取得に成功しました。', response.basic_info);
        toast.success('商談情報を取得しました');
        
        // 会議IDをURLと共に保存
        const actualMeetingId = response.basic_info.meeting_id;
        if (actualMeetingId) {
          // URLを更新
          const url = new URL(window.location.href);
          url.searchParams.set('meetingId', actualMeetingId.toString());
          window.history.pushState({}, '', url.toString());
          
          // ローカルストレージに会議IDを保存（将来の参照用）
          try {
            localStorage.setItem('lastMeetingId', actualMeetingId.toString());
          } catch (e) {
            console.warn('ローカルストレージへの保存に失敗しました', e);
          }
        }
      } else {
        console.warn('基本情報が見つかりませんでした。詳細情報:', response);
        toast.error(`商談情報が見つかりませんでした`);
        
        // 新規登録画面に戻す
        toast.error('商談情報が見つかりません。新規登録画面に戻ります。');
        setTimeout(() => {
          router.push('/newmeeting');
        }, 3000);
      }
    } catch (error) {
      console.error('基本情報の取得に失敗しました:', error);
      toast.error(`商談情報の取得に失敗しました: ${error instanceof Error ? error.message : '不明なエラー'}`);
      
      // 新規登録画面に戻す
      toast.error('商談情報の取得に失敗しました。新規登録画面に戻ります。');
      setTimeout(() => {
        router.push('/newmeeting');
      }, 3000);
    } finally {
      setIsLoading(false);
    }
  };

  // recordingBlobが更新されたら、localRecordingBlobも更新
  useEffect(() => {
    if (recordingBlob) {
      setLocalRecordingBlob(recordingBlob)
    }
  }, [recordingBlob])

  const handleStop = async () => {
    try {
      // 録音を停止
      stopRecording()
      
      // 少し長めに待機（停止処理とBlob生成を確実に待つ）
      toast.info("録音データを処理中...")
      
      // 録音データの取得を何度か試行
      const getRecordingWithRetry = async (maxRetries = 3, delayMs = 1000): Promise<Blob | null> => {
        for (let i = 0; i < maxRetries; i++) {
          // 一定時間待機
          await new Promise(resolve => setTimeout(resolve, delayMs));
          
          // 録音データを取得
          const blob = getRecordingBlob();
          
          if (blob && blob.size > 0) {
            return blob;
          }
        }
        return null;
      };
      
      // 録音データ取得を試行
      const blobToUse = await getRecordingWithRetry();
      
      // 録音データが取得できたか確認
      if (!blobToUse || blobToUse.size === 0) {
        toast.error("録音データが取得できませんでした。もう一度試してください。");
        return;
      }
      
      // 必要なデータ確認
      if (!user) {
        toast.error("ユーザー情報が取得できませんでした。ログインし直してください。");
        setTimeout(() => router.push("/"), 2000);
        return;
      }
      
      if (!meetingId) {
        toast.error("会議IDが見つかりません。正しいURLから録音ページにアクセスしてください。");
        setTimeout(() => router.push("/newmeeting"), 2000);
        return;
      }
      
      // 録音データをアップロード
      try {
        setIsUploading(true);
        toast.info("録音データをアップロード中...");
        
        // 実際のMIMEタイプを取得
        const mimeType = blobToUse.type;
        console.log("録音データのMIMEタイプ:", mimeType);
        
        // ファイル名を生成
        const userId = user.user_id;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
        const filename = `meeting_${meetingId}_user_${userId}_${timestamp}.webm`
        console.log('生成されたファイル名:', filename)
        
        // meetingIdの検証
        const meetingIdNum = parseInt(meetingId, 10);
        if (isNaN(meetingIdNum)) {
          throw new Error(`会議IDが数値ではありません: ${meetingId}`);
        }
        
        // ファイル名のmeeting_id部分を検証
        const fileNameMeetingId = filename.match(/meeting_(\d+)_/);
        if (!fileNameMeetingId || fileNameMeetingId[1] !== meetingId) {
          throw new Error("ファイル名の会議IDが一致しません");
        }
        
        // ファイルオブジェクトを作成（実際のMIMEタイプを使用）
        const file = new File([blobToUse], filename, { type: mimeType });
        
        // Azure Blob Storageにアップロード
        const blobUrl = await uploadToAzureStorage(file, filename);
        
        toast.success("録音データが保存されました");
        
        // 成功後、ダッシュボードに遷移
        setTimeout(() => {
          // ユーザーの権限に応じて適切なダッシュボードに遷移
          if (user?.account_status === 'ACTIVE' && user?.is_manager) {
            router.push('/manager-dashboard');
          } else {
            router.push('/dashboard');
          }
        }, 2000);
        
      } catch (uploadError) {
        console.error("アップロードエラー:", uploadError);
        toast.error("録音データのアップロードに失敗しました");
      } finally {
        setIsUploading(false);
      }
    } catch (error) {
      console.error("録音停止処理エラー:", error);
      toast.error("録音の停止処理中にエラーが発生しました");
    }
  };

  const handlePauseResume = () => {
    if (isPaused) {
      resumeRecording()
    } else {
      pauseRecording()
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="max-w-3xl mx-auto p-4">
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="text-xs">
                <ArrowLeft className="w-4 h-4 mr-2" />
                戻る
              </Button>
            </Link>
            <h1 className="text-lg font-semibold whitespace-nowrap">商談録音</h1>
          </div>
          
          {/* API接続状態表示 */}
          <div className={`text-xs px-2 py-1 rounded-full ${apiConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {apiConnected ? 'APIサーバー接続中' : 'APIサーバー未接続'}
          </div>
        </div>
        
        {/* API接続エラー表示 */}
        {!apiConnected && (
          <Card className="mb-4 border-red-300 bg-red-50">
            <CardContent className="py-3">
              <p className="text-sm text-red-700">
                APIサーバーに接続できません。Azure Functions が起動しているか確認してください。
                <br />
                コマンドプロンプトで <code>func start</code> を実行して Azure Functions を起動してください。
              </p>
            </CardContent>
          </Card>
        )}
        
        {/* ローディング表示 */}
        {isLoading && (
          <Card className="mb-4">
            <CardContent className="py-8">
              <div className="flex flex-col items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
                <p className="text-sm text-gray-600">商談情報を取得中...</p>
                <p className="text-xs text-gray-500 mt-2">会議ID: {meetingId} の基本情報を読み込んでいます</p>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* 以下のコンテンツは基本情報取得後またはエラー時のみ表示 */}
        {!isLoading && (
          <>
            {/* 基本情報表示 */}
            {basicInfo && (
              <BasicInfoDisplay
                clientCompanyName={basicInfo.client_company_name}
                clientContactName={basicInfo.client_contact_name}
                meetingDatetime={basicInfo.meeting_datetime}
              />
            )}

            {!isRecording && !micTested && (
              <MicrophoneTest onTestComplete={handleMicTestComplete} />
            )}

            {/* マイクテスト成功後または録音中のみ表示 */}
            {(micTested || isRecording) && !isRecording && (
              <div className="mb-4">
                <Button 
                  onClick={startRecording} 
                  className="w-full"
                  disabled={isUploading}
                >
                  <Mic className="w-4 h-4 mr-2" />
                  録音を開始
                </Button>
              </div>
            )}

            {/* 音声波形の表示 - 録音中のみ表示 */}
            {isRecording && (
              <Waveform audioLevel={audioLevel} />
            )}

            {isRecording && (
              <div className="mb-4 flex justify-between items-center">
                <div className="flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1.5">
                  <Dot
                    className={`h-5 w-5 ${isPaused ? "" : "animate-pulse"} ${isPaused ? "text-amber-500" : "text-rose-500"}`}
                  />
                  <span className="text-xs font-medium">{isPaused ? "一時停止中" : "録音中"}</span>
                  <span className="text-xs text-zinc-500">{formatTime(recordingTime)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handlePauseResume} className="text-xs" disabled={isUploading}>
                    {isPaused ? <Play className="h-4 w-4 mr-2" /> : <Pause className="h-4 w-4 mr-2" />}
                    {isPaused ? "再開" : "一時停止"}
                  </Button>
                  <Button variant="destructive" size="sm" onClick={handleStop} className="text-xs" disabled={isUploading}>
                    {isUploading ? "保存中..." : "終了"}
                  </Button>
                </div>
              </div>
            )}

            <Card className="h-[calc(100vh-220px)] sm:h-[calc(100vh-280px)]">
              <CardHeader className="border-b py-3">
                <CardTitle className="text-base">会話ログ</CardTitle>
              </CardHeader>
              <CardContent className="p-0 h-[calc(100%-57px)]">
                <div className="p-4 text-sm text-zinc-500">
                  {isRecording ? (
                    isPaused ? (
                      "録音が一時停止中です。再開ボタンをクリックして録音を続けてください。"
                    ) : (
                      "現在録音中です。会話の内容はここに表示されます。"
                    )
                  ) : (
                    "録音を開始すると、会話の内容がここに表示されます。"
                  )}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}

export default function RecordingPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <RecordingPageContent />
    </Suspense>
  )
}