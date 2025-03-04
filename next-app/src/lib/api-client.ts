/**
 * API クライアント - Azure Functions へのリクエストを処理する共通関数
 */

// API のベース URL（ローカル開発用の URL）
const API_BASE_URL = 'http://localhost:7071/api';

/**
 * HTTP リクエストを送信する汎用関数
 */
async function fetchAPI<T>(
  endpoint: string, 
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  data?: any
): Promise<T> {
  const url = `${API_BASE_URL}/${endpoint}`;
  
  console.log(`API Request: ${method} ${url}`, data);
  
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    body: data ? JSON.stringify(data) : undefined,
  };

  try {
    const response = await fetch(url, options);
    console.log(`API Response status: ${response.status}`);
    
    // レスポンスが JSON でない場合のハンドリング
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const json = await response.json();
      console.log('API Response data:', json);
      
      if (!response.ok) {
        throw new Error(json.message || json.error || 'API リクエストに失敗しました');
      }
      
      return json as T;
    } else {
      const text = await response.text();
      console.log('API Response text:', text);
      
      if (!response.ok) {
        throw new Error(text || 'API リクエストに失敗しました');
      }
      
      return text as unknown as T;
    }
  } catch (error) {
    console.error('API リクエストエラー:', error);
    throw error;
  }
}

/**
 * 商談情報を保存する
 */
export async function saveMeeting(meetingData: any): Promise<{ meetingId: number, message: string }> {
  return fetchAPI<{ meetingId: number, message: string }>('meetings', 'POST', meetingData);
}

/**
 * 基本情報を保存する
 */
export async function saveBasicInfo(basicInfoData: any): Promise<{ meetingId: number, message: string }> {
  return fetchAPI<{ meetingId: number, message: string }>('basicinfo', 'POST', basicInfoData);
}

/**
 * その他の API 関数をここに追加
 */

export default {
  saveMeeting,
  saveBasicInfo,
  // 他の API 関数
}; 