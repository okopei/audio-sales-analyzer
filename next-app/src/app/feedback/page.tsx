"use client"

import { useState, useRef, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import {
  MessageSquare,
  ChevronUp,
  ChevronDown,
  AlertCircle,
  Send,
  ArrowLeft,
  Search,
  Play,
  Pause,
  Volume2,
} from "lucide-react"
import Link from "next/link"

interface Comment {
  id: number
  author: string
  time: string
  content: string
}

interface Message {
  id: number
  content: string[]
  time: string
  speaker: "client" | "sales"
  comments: Comment[]
  isUnread: boolean
  audioUrl: string
}

interface AudioState {
  isPlaying: boolean
  currentTime: number
  duration: number
}

export default function ChatPage() {
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set())
  const [expandedComments, setExpandedComments] = useState<Set<number>>(new Set())
  const [playingAudio, setPlayingAudio] = useState<number | null>(null)
  const [audioStates, setAudioStates] = useState<{ [key: number]: AudioState }>({})
  const audioRefs = useRef<{ [key: number]: HTMLAudioElement }>({})
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      content: [
        "本日は弊社製品のご提案の機会をいただき、ありがとうございます。",
        "まずは御社の現状の課題についてお伺いさせていただきます。",
        "弊社の製品がどのようにお役に立てるか、具体的にご説明させていただきます。",
        "どのような点でお困りでしょうか？",
      ],
      time: "14:00",
      speaker: "sales",
      comments: [
        {
          id: 1,
          author: "山田 部長",
          time: "1/25日 15:30",
          content: "導入事例を交えて説明できていて良いです。",
        },
      ],
      isUnread: true,
      audioUrl: "/placeholder.mp3",
    },
    {
      id: 2,
      content: [
        "現在、手作業での管理に多くの工数がかかっています。",
        "特に月次レポートの作成に問題を抱えています。",
        "データの集計や分析に時間がかかり過ぎているのが現状です。",
        "自動化による工数削減に興味があります。",
      ],
      time: "14:05",
      speaker: "client",
      comments: [],
      isUnread: false,
      audioUrl: "/placeholder.mp3",
    },
    {
      id: 3,
      content: [
        "承知いたしました。月次レポートの作成に関する課題について、詳しくお聞かせいただきありがとうございます。",
        "弊社の自動化ソリューションは、データ集計や分析プロセスを大幅に効率化できます。",
        "例えば、同業他社での導入事例では、レポート作成時間が約70%削減されました。",
        "御社の具体的な業務フローについて、もう少し詳しくお聞かせいただけますでしょうか？",
      ],
      time: "14:07",
      speaker: "sales",
      comments: [
        {
          id: 2,
          author: "鈴木 次長",
          time: "1/25日 15:45",
          content: "課題の具体化ができています。良い流れです。",
        },
      ],
      isUnread: true,
      audioUrl: "/placeholder.mp3",
    },
  ])
  const [newComments, setNewComments] = useState<{ [key: number]: string }>({})
  const [showAudioControl, setShowAudioControl] = useState<number | null>(null)

  useEffect(() => {
    messages.forEach((message) => {
      const audio = new Audio(message.audioUrl)
      audioRefs.current[message.id] = audio
      audio.addEventListener("loadedmetadata", () => {
        setAudioStates((prev) => ({
          ...prev,
          [message.id]: { isPlaying: false, currentTime: 0, duration: audio.duration },
        }))
      })
      audio.addEventListener("timeupdate", () => {
        setAudioStates((prev) => ({
          ...prev,
          [message.id]: { ...prev[message.id], currentTime: audio.currentTime },
        }))
      })
      audio.addEventListener("ended", () => {
        setAudioStates((prev) => ({
          ...prev,
          [message.id]: { ...prev[message.id], isPlaying: false, currentTime: 0 },
        }))
        setPlayingAudio(null)
      })
    })

    return () => {
      Object.values(audioRefs.current).forEach((audio) => {
        audio.pause()
        audio.currentTime = 0
      })
    }
  }, [messages])

  const toggleMessageExpand = (id: number) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const toggleCommentsExpand = (id: number) => {
    setExpandedComments((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
    markAsRead(id)
  }

  const markAsRead = (id: number) => {
    setMessages((prevMessages) => prevMessages.map((msg) => (msg.id === id ? { ...msg, isUnread: false } : msg)))
  }

  const handleNewComment = (messageId: number) => {
    const commentContent = newComments[messageId]
    if (!commentContent || commentContent.trim() === "") return

    const newComment: Comment = {
      id: Date.now(),
      author: "現在のユーザー",
      time: new Date().toLocaleString(),
      content: commentContent.trim(),
    }

    setMessages((prevMessages) =>
      prevMessages.map((msg) =>
        msg.id === messageId ? { ...msg, comments: [...msg.comments, newComment], isUnread: true } : msg,
      ),
    )

    setNewComments((prev) => ({ ...prev, [messageId]: "" }))
  }

  const toggleAudio = (id: number) => {
    const audio = audioRefs.current[id]
    if (playingAudio === id) {
      audio.pause()
      setPlayingAudio(null)
      setAudioStates((prev) => ({ ...prev, [id]: { ...prev[id], isPlaying: false } }))
    } else {
      if (playingAudio !== null) {
        audioRefs.current[playingAudio].pause()
        setAudioStates((prev) => ({ ...prev, [playingAudio]: { ...prev[playingAudio], isPlaying: false } }))
      }
      audio.play()
      setPlayingAudio(id)
      setAudioStates((prev) => ({ ...prev, [id]: { ...prev[id], isPlaying: true } }))
    }
  }

  const handleSeek = (id: number, value: number[]) => {
    const audio = audioRefs.current[id]
    audio.currentTime = value[0]
    setAudioStates((prev) => ({ ...prev, [id]: { ...prev[id], currentTime: value[0] } }))
  }

  const toggleAudioControl = (id: number) => {
    setShowAudioControl((prevId) => (prevId === id ? null : id))
  }

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }

  const AudioControl = ({ message }: { message: Message }) => {
    const audioState = audioStates[message.id] || { isPlaying: false, currentTime: 0, duration: 0 }

    return (
      <div className="flex items-center gap-1 mt-1 text-xs">
        <Button variant="ghost" size="sm" onClick={() => toggleAudio(message.id)} className="p-1 h-6 w-6">
          {audioState.isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </Button>
        <Slider
          value={[audioState.currentTime]}
          max={audioState.duration}
          step={0.1}
          onValueChange={(value) => handleSeek(message.id, value)}
          className="w-24 sm:w-32"
        />
        <span className="text-gray-500 min-w-[60px]">
          {formatTime(audioState.currentTime)} / {formatTime(audioState.duration)}
        </span>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="max-w-3xl mx-auto p-4">
        <div className="mb-4 flex justify-between items-center">
          <Link href="/dashboard">
            <Button variant="outline" size="sm" className="text-xs md:text-sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              ダッシュボードに戻る
            </Button>
          </Link>
          <Link href="/search">
            <Button variant="outline" size="sm" className="text-xs md:text-sm">
              <Search className="w-4 h-4 mr-2" />
              商談検索
            </Button>
          </Link>
        </div>
        <Card className="p-6 text-sm md:text-base">
          <div className="mb-6">
            <h1 className="text-lg md:text-xl font-semibold">商談：株式会社ABC 様</h1>
            <p className="text-xs md:text-sm text-gray-500">2024年1月25日 14:00-15:00</p>
          </div>

          <div className="space-y-6">
            {messages.map((message) => {
              const isExpanded = expandedMessages.has(message.id)
              const areCommentsExpanded = expandedComments.has(message.id)

              return (
                <div
                  key={message.id}
                  className={`space-y-2 relative ${message.speaker === "client" ? "ml-12" : "mr-12"}`}
                >
                  {message.isUnread && <AlertCircle className="absolute top-0 right-0 h-5 w-5 text-red-500" />}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs md:text-sm text-gray-500">
                      <span>{message.time}</span>
                      <span className="font-medium">{message.speaker === "sales" ? "営業担当" : "お客様"}</span>
                    </div>
                    <div
                      className={`rounded-lg p-3 relative ${
                        message.speaker === "sales" ? "bg-blue-50 rounded-tr-none" : "bg-green-50 rounded-tl-none"
                      }`}
                    >
                      <p className="text-sm md:text-base">{message.content[0]}</p>
                      {message.content.length > 2 && (
                        <>
                          {isExpanded ? (
                            <>
                              <p className="mt-1 text-sm md:text-base">{message.content[1]}</p>
                              <p className="mt-1 text-sm md:text-base">{message.content[2]}</p>
                            </>
                          ) : (
                            <p className="mt-1 text-gray-500">...</p>
                          )}
                        </>
                      )}
                      <p className="mt-1 text-sm md:text-base">{message.content[message.content.length - 1]}</p>
                      <div className="flex justify-between items-center mt-1">
                        <div className="flex items-center gap-1">
                          {message.content.length > 2 && (
                            <button
                              onClick={() => toggleMessageExpand(message.id)}
                              className="text-blue-500 hover:underline text-xs"
                            >
                              {isExpanded ? "閉じる" : "全文を表示"}
                            </button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleAudioControl(message.id)}
                            className="text-gray-500 hover:text-gray-700 p-0.5 h-5 w-5"
                          >
                            <Volume2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                      {showAudioControl === message.id && <AudioControl message={message} />}
                    </div>

                    <div className="pl-4 border-l-2 border-gray-200">
                      <button
                        onClick={() => toggleCommentsExpand(message.id)}
                        className="flex items-center text-xs md:text-sm text-gray-500 hover:text-gray-700"
                      >
                        <MessageSquare className="h-4 w-4 mr-1" />
                        コメント ({message.comments.length})
                        {areCommentsExpanded ? (
                          <ChevronUp className="h-4 w-4 ml-1" />
                        ) : (
                          <ChevronDown className="h-4 w-4 ml-1" />
                        )}
                      </button>

                      {areCommentsExpanded && (
                        <div className="mt-2 space-y-2">
                          {message.comments.map((comment) => (
                            <div key={comment.id} className="flex items-start gap-2 bg-white p-2 rounded-md">
                              <div>
                                <div className="flex gap-2 items-baseline">
                                  <span className="text-xs md:text-sm font-medium">{comment.author}</span>
                                  <span className="text-[10px] md:text-xs text-gray-500">{comment.time}</span>
                                </div>
                                <p className="text-xs md:text-sm">{comment.content}</p>
                              </div>
                            </div>
                          ))}
                          <div className="flex items-center gap-2 mt-2">
                            <Input
                              type="text"
                              placeholder="コメントを入力..."
                              value={newComments[message.id] || ""}
                              onChange={(e) => setNewComments({ ...newComments, [message.id]: e.target.value })}
                              className="text-xs md:text-sm flex-grow"
                            />
                            <Button size="sm" onClick={() => handleNewComment(message.id)} className="px-2 py-1">
                              <Send className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>
    </div>
  )
}

