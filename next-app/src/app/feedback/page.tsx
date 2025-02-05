'use client'

import { useState } from "react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { MessageCircle, X, ChevronLeft } from "lucide-react"
import { useSpring, animated } from "@react-spring/web"
import { useDrag } from "@use-gesture/react"

type Message = {
  id: number
  sender: "sales" | "client"
  content: string[]
  hiddenContent: string
  additionalContent: string[]
  time: string
  comments: Array<{
    author: string
    role: string
    time: string
    content: string
  }>
}

export default function ChatPage() {
  const [activeCommentId, setActiveCommentId] = useState<number | null>(null)
  const [openFullContent, setOpenFullContent] = useState<number[]>([])
  const [{ x }, api] = useSpring(() => ({ x: 0 }))

  const messages: Message[] = [
    {
      id: 1,
      sender: "sales",
      content: [
        "本日は弊社製品のご提案の機会をいただき、ありがとうございます。",
        "まずは御社の現状の課題についてお伺いできればと思います。",
      ],
      hiddenContent: "xxxxxx",
      additionalContent: [
        "既に作成した画面（ダッシュボード、録音画面、チャット画面）でもこれらの技術を使用しています。",
        "何か具体的に試してみたい機能はありますか？",
      ],
      time: "14:00",
      comments: [
        {
          author: "山田",
          role: "部長",
          time: "1/25日 15:30",
          content:
            "導入事例を具体的に説明できていて良いですね。次回は具体的な数値を含める事で、より説得力が増すと思います。",
        },
      ],
    },
    {
      id: 2,
      sender: "client",
      content: [
        "現在、手作業での管理に多くの工数がかかっています。",
        "特に月次レポートの作成に問題がかかっているんです。",
      ],
      hiddenContent: "xxxxxx",
      additionalContent: [
        "既に作成した画面（ダッシュボード、録音画面、チャット画面）でもこれらの技術を使用しています。",
        "何か具体的に試してみたい機能はありますか？",
      ],
      time: "14:05",
      comments: [],
    },
    {
      id: 3,
      sender: "sales",
      content: ["ご提案した自動化ソリューションについて、", "具体的な導入コストをご提示できますでしょうか。"],
      hiddenContent: "xxxxxx",
      additionalContent: [
        "既に作成した画面（ダッシュボード、録音画面、チャット画面）でもこれらの技術を使用しています。",
        "何か具体的に試してみたい機能はありますか？",
      ],
      time: "14:45",
      comments: [
        {
          author: "鈴木",
          role: "石雄",
          time: "1/25日 16:00",
          content:
            "承知しました。次回商談時は、同業他社での導入後の工数削減効果（約30%削減）についてお話しさせていただきます。",
        },
      ],
    },
  ]

  const toggleFullContent = (id: number) => {
    setOpenFullContent((prev) => (prev.includes(id) ? prev.filter((messageId) => messageId !== id) : [...prev, id]))
  }

  const toggleComments = (id: number) => {
    setActiveCommentId(activeCommentId === id ? null : id)
  }

  const closeComments = () => {
    setActiveCommentId(null)
  }

  const bind = useDrag(
    ({ down, movement: [mx], direction: [dx], cancel }) => {
      if (down && mx > 50 && dx > 0) {
        cancel()
        closeComments()
      }
      api.start({ x: down ? mx : 0, immediate: down })
    },
    { axis: "x" },
  )

  const salesBubbleColor = "bg-zinc-700"
  const clientBubbleColor = "bg-zinc-600"
  const salesBubbleTipColor = "before:border-l-zinc-700 before:border-t-zinc-700"
  const clientBubbleTipColor = "before:border-r-zinc-600 before:border-t-zinc-600"

  return (
    <div className="min-h-screen bg-[#1F1F1F]">
      <header className="border-b border-zinc-800 bg-zinc-900 px-2 sm:px-4 py-3">
        <div className="mx-auto max-w-[1200px] flex items-center">
          <Button
            variant="ghost"
            size="sm"
            className="mr-2 text-white hover:bg-zinc-800 transition-colors duration-200 p-2"
            aria-label="戻る"
          >
            <ChevronLeft className="h-6 w-6" />
          </Button>
          <div className="flex-1 flex items-center justify-between">
            <div>
              <h1 className="text-lg font-medium text-white">商談：株式会社ABC 様</h1>
              <p className="text-sm text-zinc-400">2024年1月25日 14:00-15:00</p>
            </div>
            <Button variant="outline" className="border-zinc-700 bg-zinc-800 text-white hover:bg-zinc-700">
              <MessageCircle className="h-4 w-4 mr-2" />
              コメント
            </Button>
          </div>
        </div>
      </header>

      <animated.div
        {...bind()}
        style={{ x }}
        className="mx-auto max-w-[1200px] grid grid-cols-1 md:grid-cols-[150px_1fr_260px] gap-4 p-4"
      >
        <div className="hidden md:block space-y-4">
          <Card className="bg-zinc-900 border-zinc-800 p-4">
            <h2 className="text-sm font-medium text-white mb-2">商談情報</h2>
            <div className="space-y-2">
              <div className="text-xs text-zinc-400">
                <div className="font-medium text-rose-400">ステータス</div>
                <div>見積書作成</div>
              </div>
              <div className="text-xs text-zinc-400">
                <div className="font-medium text-rose-400">アクション</div>
                <div>見積書作成</div>
              </div>
              <div className="text-xs text-zinc-400">
                <div className="font-medium text-rose-400">進捗</div>
                <div>1/30</div>
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-4 max-w-full md:max-w-[800px]">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.sender === "sales" ? "flex-row-reverse" : ""} gap-4`}>
              <Avatar className="h-8 w-8 flex-shrink-0 mt-1">
                <AvatarImage src="/placeholder.svg" alt={message.sender === "sales" ? "S" : "C"} />
                <AvatarFallback className={message.sender === "sales" ? "bg-rose-500" : "bg-blue-500"}>
                  {message.sender === "sales" ? "S" : "C"}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 space-y-1">
                <div
                  className={`relative rounded-lg ${
                    message.sender === "sales" ? salesBubbleColor : clientBubbleColor
                  } p-4 text-sm text-white before:content-[''] before:absolute before:border-8 ${
                    message.sender === "sales"
                      ? `before:-right-4 ${salesBubbleTipColor} before:border-r-transparent before:border-b-transparent mr-2`
                      : `before:-left-4 ${clientBubbleTipColor} before:border-l-transparent before:border-b-transparent ml-2`
                  } before:top-4`}
                >
                  {message.content.map((text, index) => (
                    <p key={index} className={index > 0 ? "mt-2" : ""}>
                      {text}
                    </p>
                  ))}
                  <button
                    className="mt-2 text-xs text-rose-400 hover:underline block w-full text-center"
                    onClick={() => toggleFullContent(message.id)}
                  >
                    [クリックで全文表示]
                  </button>
                  {openFullContent.includes(message.id) && <p className="mt-2">{message.hiddenContent}</p>}
                  {message.additionalContent.map((text, index) => (
                    <p key={`additional-${index}`} className="mt-2">
                      {text}
                    </p>
                  ))}
                  {message.comments.length > 0 && (
                    <div className="absolute -right-2 -top-2 w-4 h-4 bg-pink-500 rounded-full"></div>
                  )}
                  <div className={`flex mt-2 ${message.sender === "sales" ? "justify-start" : "justify-end"}`}>
                    <div
                      className={`text-xs text-zinc-400 ${message.sender === "sales" ? "order-2 ml-2" : "order-1 mr-2"}`}
                    >
                      {message.time}
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      className={`bg-pink-700 hover:bg-pink-600 text-white ${message.sender === "sales" ? "order-1" : "order-2"}`}
                      onClick={() => toggleComments(message.id)}
                    >
                      Comment
                    </Button>
                  </div>
                </div>
                {activeCommentId === message.id && (
                  <div className="mt-2 md:hidden">
                    <Card className="bg-zinc-900 border-zinc-800 p-4">
                      <div className="flex items-center justify-between mb-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-zinc-400 hover:text-white p-0"
                          onClick={closeComments}
                        >
                          <ChevronLeft className="h-4 w-4 mr-1" />
                          戻る
                        </Button>
                        <h2 className="text-sm font-medium text-white">コメント</h2>
                      </div>
                      {message.comments.length > 0 ? (
                        <div className="space-y-4">
                          {message.comments.map((comment, index) => (
                            <div key={index} className="space-y-2">
                              <div className="flex items-start gap-2">
                                <Avatar className="h-6 w-6">
                                  <AvatarImage src="/placeholder.svg" alt={comment.author} />
                                  <AvatarFallback className="bg-pink-500 text-xs">{comment.author[0]}</AvatarFallback>
                                </Avatar>
                                <div>
                                  <div className="text-xs font-medium text-white">
                                    {comment.author} {comment.role}
                                  </div>
                                  <div className="text-xs text-zinc-400">{comment.time}</div>
                                </div>
                              </div>
                              <p className="text-xs text-zinc-200">{comment.content}</p>
                            </div>
                          ))}
                          <div className="border-t border-zinc-800 mt-4 pt-4" />
                        </div>
                      ) : (
                        <div className="text-xs text-zinc-400 mb-4">まだコメントはありません</div>
                      )}
                      <div className="space-y-2">
                        <Textarea
                          placeholder="コメントを入力..."
                          className="min-h-[80px] bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400 text-xs"
                        />
                        <Button className="w-full bg-pink-600 text-white hover:bg-pink-500 text-xs">
                          コメントを送信
                        </Button>
                      </div>
                    </Card>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="hidden md:block space-y-4 md:w-[260px]">
          {activeCommentId ? (
            <Card className="bg-zinc-900 border-zinc-800 p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-medium text-white">コメント</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-zinc-400 hover:text-white"
                  onClick={() => setActiveCommentId(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div className="space-y-4">
                {messages
                  .find((m) => m.id === activeCommentId)
                  ?.comments.map((comment, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-start gap-2">
                        <Avatar className="h-6 w-6">
                          <AvatarImage src="/placeholder.svg" alt={comment.author} />
                          <AvatarFallback className="bg-pink-500 text-xs">{comment.author[0]}</AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="text-xs font-medium text-white">
                            {comment.author} {comment.role}
                          </div>
                          <div className="text-xs text-zinc-400">{comment.time}</div>
                        </div>
                      </div>
                      <p className="text-xs text-zinc-200">{comment.content}</p>
                    </div>
                  ))}
              </div>

              <div className="mt-4">
                <Textarea
                  placeholder="コメントを入力..."
                  className="min-h-[80px] bg-zinc-800 border-zinc-700 text-white placeholder-zinc-400"
                />
                <Button className="mt-2 w-full bg-pink-600 text-white hover:bg-pink-500">送信</Button>
              </div>
            </Card>
          ) : (
            <Card className="bg-zinc-900 border-zinc-800 p-4">
              <div className="text-sm text-zinc-400 text-center">
                コメントを表示するには、メッセージの「Comment」をクリックしてください
              </div>
            </Card>
          )}
        </div>
      </animated.div>
    </div>
  )
}

