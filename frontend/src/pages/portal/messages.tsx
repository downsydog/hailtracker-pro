import * as React from "react"
import { useSearchParams } from "react-router-dom"
import { portalApi, PortalMessage } from "@/api/portal"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import {
  MessageSquare,
  Send,
  Paperclip,
  User,
  Users,
  Check,
  CheckCheck,
} from "lucide-react"

export function PortalMessagesPage() {
  const [searchParams] = useSearchParams()
  const jobFilter = searchParams.get("job_id")
  const [messages, setMessages] = React.useState<PortalMessage[]>([])
  const [loading, setLoading] = React.useState(true)
  const [newMessage, setNewMessage] = React.useState("")
  const [sending, setSending] = React.useState(false)
  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const fetchMessages = async () => {
      try {
        const result = await portalApi.getMessages(jobFilter ? Number(jobFilter) : undefined)
        setMessages(result.messages)
      } catch {
        // Demo data
        setMessages([
          {
            id: 1,
            job_id: 1,
            sender_type: "staff",
            sender_name: "Sarah - Service Advisor",
            message: "Hi! Your vehicle has been checked in. We'll begin the inspection shortly and send you an estimate.",
            created_at: "2025-01-20T10:00:00",
          },
          {
            id: 2,
            job_id: 1,
            sender_type: "customer",
            sender_name: "You",
            message: "Thanks! About how long will the repair take?",
            read_at: "2025-01-20T10:05:00",
            created_at: "2025-01-20T10:03:00",
          },
          {
            id: 3,
            job_id: 1,
            sender_type: "staff",
            sender_name: "Sarah - Service Advisor",
            message: "Based on initial assessment, we estimate 5-7 business days for the hail damage repair. I'll confirm once we complete the full inspection.",
            created_at: "2025-01-20T10:30:00",
          },
          {
            id: 4,
            job_id: 1,
            sender_type: "staff",
            sender_name: "Mike - Technician",
            message: "I've started work on your vehicle. The hood and roof had the most damage. I'll send progress photos later today.",
            created_at: "2025-01-21T09:00:00",
          },
          {
            id: 5,
            job_id: 1,
            sender_type: "staff",
            sender_name: "Mike - Technician",
            message: "Here are today's progress photos. Hood is about 70% complete!",
            attachments: ["/photo1.jpg", "/photo2.jpg"],
            created_at: "2025-01-22T15:30:00",
          },
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchMessages()
  }, [jobFilter])

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    if (!newMessage.trim()) return

    setSending(true)
    try {
      // In real app, would use portalApi.sendMessage
      const newMsg: PortalMessage = {
        id: Date.now(),
        job_id: jobFilter ? Number(jobFilter) : 1,
        sender_type: "customer",
        sender_name: "You",
        message: newMessage,
        created_at: new Date().toISOString(),
      }
      setMessages([...messages, newMsg])
      setNewMessage("")
    } catch (error) {
      console.error("Failed to send message:", error)
    } finally {
      setSending(false)
    }
  }

  const formatTime = (date: string) => {
    const d = new Date(date)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (d.toDateString() === today.toDateString()) {
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    } else if (d.toDateString() === yesterday.toDateString()) {
      return `Yesterday ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
    } else {
      return d.toLocaleDateString([], { month: "short", day: "numeric" }) +
        " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Messages</h1>
        <p className="text-muted-foreground">
          Communicate with our team about your repair
        </p>
      </div>

      <Card className="flex flex-col h-[calc(100vh-280px)] min-h-[500px]">
        <CardHeader className="border-b pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-5 w-5" />
            {jobFilter ? `Job #JOB-2025-${jobFilter.padStart(3, "0")}` : "All Messages"}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length > 0 ? (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-3",
                    message.sender_type === "customer" ? "flex-row-reverse" : ""
                  )}
                >
                  <div className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0",
                    message.sender_type === "customer" ? "bg-blue-100" : "bg-gray-100"
                  )}>
                    <User className={cn(
                      "h-4 w-4",
                      message.sender_type === "customer" ? "text-blue-600" : "text-gray-600"
                    )} />
                  </div>
                  <div className={cn(
                    "max-w-[75%]",
                    message.sender_type === "customer" ? "text-right" : ""
                  )}>
                    <div className={cn(
                      "text-xs text-muted-foreground mb-1",
                      message.sender_type === "customer" ? "text-right" : ""
                    )}>
                      {message.sender_name}
                    </div>
                    <div className={cn(
                      "rounded-lg p-3 inline-block text-left",
                      message.sender_type === "customer"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100"
                    )}>
                      <p className="text-sm">{message.message}</p>
                      {message.attachments && message.attachments.length > 0 && (
                        <div className="mt-2 flex gap-2 flex-wrap">
                          {message.attachments.map((_att, i) => (
                            <div
                              key={i}
                              className="h-16 w-16 rounded bg-white/20 flex items-center justify-center text-xs"
                            >
                              Photo {i + 1}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className={cn(
                      "text-xs text-muted-foreground mt-1 flex items-center gap-1",
                      message.sender_type === "customer" ? "justify-end" : ""
                    )}>
                      {formatTime(message.created_at)}
                      {message.sender_type === "customer" && (
                        message.read_at ? (
                          <CheckCheck className="h-3 w-3 text-blue-500" />
                        ) : (
                          <Check className="h-3 w-3" />
                        )
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <p className="font-medium">No messages yet</p>
                <p className="text-sm text-muted-foreground">
                  Start a conversation with our team
                </p>
              </div>
            </div>
          )}
        </CardContent>

        {/* Message Input */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Button variant="ghost" size="icon" type="button">
              <Paperclip className="h-5 w-5" />
            </Button>
            <Input
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Type your message..."
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
            />
            <Button onClick={handleSend} disabled={sending || !newMessage.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Messages are typically answered within 1-2 hours during business hours
          </p>
        </div>
      </Card>
    </div>
  )
}
