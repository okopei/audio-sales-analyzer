対象ディレクトリ
audio-sales-analyzer/saa-api-func/function_app.py

APIエンドポイント一覧（Azure Functions）
function_app.py に定義された HTTP トリガー関数のエンドポイント一覧です。

認証系
POST api/users/login：ログイン処理（パスワード認証）
  ↳ 使用画面：`next-app/src/hooks/useAuth.tsx`
GET api/users/id/{user_id}：ユーザー情報取得
  ↳ 使用画面：`next-app/src/hooks/useUser.tsx`
GET api/users：ユーザー一覧取得
  ↳ 使用画面：`next-app/src/app/search/page.tsx`

会議関連
POST api/basicinfo：会議の基本情報を保存
  ↳ 使用画面：`next-app/src/app/newmeeting/page.tsx`
GET api/basicinfo/{meeting_id}：会議の基本情報を取得
  ↳ 使用画面：`next-app/src/app/feedback/[meeting_id]/page.tsx`
GET api/meetings：会議一覧検索（クエリで絞り込み可能）
  ↳ 使用画面：`next-app/src/app/search/page.tsx`
GET api/members-meetings?manager_id=...：上司IDから部下の会議一覧を取得
  ↳ 使用画面：`next-app/src/hooks/useMembersMeetings.tsx`

コメント関連
POST api/comments：コメントを追加
  ↳ 使用画面：`next-app/src/app/feedback/[meeting_id]/page.tsx`
GET api/comments/{segment_id}：セグメント単位のコメント取得
  ↳ 使用画面：`next-app/src/app/feedback/[meeting_id]/page.tsx`
GET api/comments/by-meeting/{meeting_id}：会議単位のコメント取得
  ↳ 使用画面：`next-app/src/components/comments/CommentsList.tsx`
GET api/comments-latest?userId=...：最新コメント（ユーザー単位）取得
  ↳ 使用画面：`next-app/src/app/dashboard/page.tsx`, `next-app/src/app/manager-dashboard/page.tsx`
POST api/comments/read：コメントの既読状態を登録
  ↳ 使用画面：`next-app/src/components/feedback/read-button.tsx`
DELETE api/comments/{comment_id}：コメントの論理削除
  ↳ 使用画面：`next-app/src/app/feedback/[meeting_id]/page.tsx`
GET api/comment-read-status?userId=...&commentId=...：コメントの既読状況を取得
  ↳ 使用画面：`next-app/src/app/dashboard/page.tsx`, `next-app/src/app/manager-dashboard/page.tsx`

会話セグメント
GET api/conversation/segments/{meeting_id}：会議IDに紐づく発話セグメント一覧を取得
  ↳ 使用画面：`next-app/src/app/feedback/[meeting_id]/page.tsx`

ユーティリティ
GET api/testdb：DB接続テスト（user_id=27固定）