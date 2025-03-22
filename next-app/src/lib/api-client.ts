/**
 * API クライアント - Azure Functions へのリクエストを処理する共通関数
 */

// API のベース URL（ローカル開発用の URL）
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7071/api';

// 初期化時にAPIのベースURLをログに出力
console.log(`API Base URL configured as: ${API_BASE_URL}`);

// BasicInfoデータの型定義
export interface BasicInfoData {
  userId: string | number;
  year: string;
  month: string;
  day: string;
  hour: string;
  companyName: string;
  client_company_name: string;
  client_contact_name: string;
  industry?: string;
  scale?: string;
  meeting_goal?: string;
  meeting_datetime?: string;
}

// 基本情報検索結果の型定義
export interface BasicInfoSearchResult {
  basic_info?: any;
  found: boolean;
  message?: string;
  meeting_id?: number;
  search_params?: {
    user_id: number;
    client_company_name?: string;
    client_contact_name?: string;
    meeting_datetime?: string;
  };
}

/**
 * HTTP リクエストを送信する汎用関数
 */
async function fetchAPI(endpoint: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE_URL}${endpoint}`;
  console.log(`API リクエスト: ${options.method || 'GET'} ${url}`, options);

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    // レスポンスをログに出力
    console.log(`APIレスポンスステータス: ${response.status}`);

    // 応答がJSONかどうかを確認
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');

    if (isJson) {
      const data = await response.json();
      console.log('APIレスポンスデータ:', data);

      // 特別なケース: "No basic info found"というメッセージが含まれる404や500エラーは
      // 有効なレスポンスとして扱う（検索結果が見つからない場合）
      if (!response.ok && 
          (response.status === 404 || response.status === 500) && 
          data.message && 
          data.message.includes('No basic info found')) {
        return data;
      }

      // エラーチェック
      if (!response.ok) {
        // データベース接続エラーの特別処理
        if (data.error && data.error.includes('Error retrieving inserted record ID')) {
          throw new Error('データベース接続エラーが発生しました。サーバー管理者に連絡してください。');
        }

        // 一般的なエラー
        const message = data.message || data.error || 'APIエラーが発生しました';
        throw new Error(message);
      }

      return data;
    } else {
      // JSON以外のレスポンス
      const text = await response.text();
      console.log('APIレスポンステキスト:', text);

      if (!response.ok) {
        throw new Error(`APIエラー: ${response.status} ${response.statusText}`);
      }

      return { text };
    }
  } catch (error) {
    console.error('API呼び出しエラー:', error);
    throw error;
  }
}

/**
 * 商談情報を保存する
 */
export async function saveMeeting(meetingData: any): Promise<{ meetingId: number, message: string }> {
  const response = await fetchAPI('/meetings', {
    method: 'POST',
    body: JSON.stringify(meetingData)
  });
  
  return response;
}

/**
 * 基本情報を保存する
 */
export async function saveBasicInfo(basicInfoData: BasicInfoData): Promise<{ success: boolean, message: string, search_info: any }> {
  try {
    console.log('基本情報を保存中:', basicInfoData);

    const response = await fetchAPI('/basicinfo', {
      method: 'POST',
      body: JSON.stringify(basicInfoData),
    });

    if (!response || !response.success) {
      console.error('基本情報の保存に失敗しました:', response);
      throw new Error('基本情報の保存に失敗しました');
    }

    console.log('基本情報が正常に保存されました。検索情報:', response.search_info);
    
    // 基本情報をローカルストレージに保存（録音画面での検索用）
    if (typeof window !== 'undefined' && response.search_info) {
      try {
        localStorage.setItem('basicMeetingInfo', JSON.stringify(response.search_info));
        console.log('基本情報をローカルストレージに保存しました');
      } catch (storageError) {
        console.warn('ローカルストレージへの保存に失敗:', storageError);
      }
    }
    
    return response;
  } catch (error: any) {
    console.error('基本情報の保存中にエラーが発生しました:', error);

    // データベース接続エラーの特別処理
    if (error.message && (
      error.message.includes('データベース接続エラー') ||
      error.message.includes('SQLDriverConnect') ||
      error.message.includes('SQL Server') ||
      error.message.includes('Error retrieving inserted record ID')
    )) {
      throw new Error('データベース接続エラーが発生しました。Azure FunctionsのSqlConnectionString設定を確認してください。');
    }

    throw error;
  }
}

/**
 * Azure Blob Storageにアップロードした音声ファイル情報をMeetingsテーブルに保存する
 */
export async function updateMeetingWithRecording(data: {
  meetingId: number;
  userId: number;
  fileName: string;
  filePath: string;
  fileSize: number;
  durationSeconds: number;
  clientCompanyName: string;
  clientContactName: string;
  meetingDatetime: string;
}): Promise<{ success: boolean; message: string }> {
  const response = await fetchAPI('/meetings/update-recording', {
    method: 'POST',
    body: JSON.stringify(data)
  });
  
  return response;
}

/**
 * 会議IDに基づいて基本情報を取得する
 */
export async function getBasicInfo(meetingId: string | number, userId?: string | number): Promise<BasicInfoSearchResult> {
  const params = new URLSearchParams();
  if (userId) params.append('user_id', userId.toString());
  
  const endpoint = meetingId === 'search' 
    ? `/basicinfo/search?${params.toString()}`
    : `/basicinfo/${meetingId}?${params.toString()}`;
  
  return fetchAPI(endpoint);
}

/**
 * 詳細検索で基本情報を取得する
 */
export async function searchBasicInfo(
  userId: string | number, 
  companyName?: string,
  contactName?: string,
  meetingDateTime?: string
): Promise<BasicInfoSearchResult> {
  const params = new URLSearchParams();
  params.append('user_id', userId.toString());
  if (companyName) params.append('company_name', companyName);
  if (contactName) params.append('contact_name', contactName);
  if (meetingDateTime) params.append('meeting_datetime', meetingDateTime);
  
  return fetchAPI(`/basicinfo/search?${params.toString()}`);
}

/**
 * APIサーバーの状態を確認する
 */
export async function checkApiHealth(): Promise<{ status: string; message: string }> {
  const response = await fetchAPI('/health', { method: 'GET' });
  return response;
}

/**
 * ローカルストレージから基本情報を取得
 */
export function getStoredBasicInfo(): {
  client_company_name: string;
  client_contact_name: string;
  meeting_datetime: string;
  user_id?: string | number;
} | null {
  if (typeof window === 'undefined') return null;
  
  try {
    const storedInfo = localStorage.getItem('basicMeetingInfo');
    if (!storedInfo) return null;
    
    return JSON.parse(storedInfo);
  } catch (error) {
    console.error('ローカルストレージからの読み込みに失敗:', error);
    return null;
  }
}

/**
 * その他の API 関数をここに追加
 */

export default {
  saveMeeting,
  saveBasicInfo,
  updateMeetingWithRecording,
  getBasicInfo,
  searchBasicInfo,
  checkApiHealth,
  getStoredBasicInfo,
  // 他の API 関数
}; 