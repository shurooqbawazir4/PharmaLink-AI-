"use client";

import { useState } from "react";
import { Sparkles, User } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { HospitalScopeSelect } from "@/components/layout/HospitalScopeSelect";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@/features/assistant/hooks";
import { useHospitalScope } from "@/hooks/useHospitalScope";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";

// The spec's own example questions — one click drops them into the input.
const EXAMPLE_QUESTIONS = [
  "Why should I transfer?",
  "Why buy now?",
  "What is my highest risk medicine?",
  "Which hospital needs insulin?",
];

export default function AssistantPage() {
  const scope = useHospitalScope();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const chat = useChat();

  const send = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || chat.isPending) return;
    const history = messages;
    const userMessage: ChatMessage = { role: "user", content: trimmed };
    setMessages([...history, userMessage]);
    setInput("");
    chat.mutate(
      { question: trimmed, history, hospital_id: scope.hospitalId },
      {
        onSuccess: (response) => {
          setMessages((prev) => [...prev, { role: "assistant", content: response.answer }]);
        },
        onError: () => {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "Sorry — couldn't reach the assistant just now. Try again." },
          ]);
        },
      }
    );
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <PageHeader
        title="AI Assistant"
        description="Explanation only, grounded in real numbers — it never predicts, only narrates what the pipeline already computed."
        actions={<HospitalScopeSelect scope={scope} />}
      />

      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardContent className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Sparkles className="h-6 w-6" />
              </div>
              <div>
                <p className="font-medium">Ask about demand, risk, or a recommendation</p>
                <p className="text-sm text-muted-foreground">
                  Scoped to {scope.isAdmin ? "the network (or pick a hospital above)" : "your hospital"}.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {EXAMPLE_QUESTIONS.map((question) => (
                  <Button key={question} variant="outline" size="sm" onClick={() => send(question)}>
                    {question}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => <ChatBubble key={index} message={message} />)
          )}
          {chat.isPending && <ChatBubble message={{ role: "assistant", content: "Thinking…" }} pending />}
        </CardContent>

        <form
          className="flex items-end gap-2 border-t p-3"
          onSubmit={(event) => {
            event.preventDefault();
            send(input);
          }}
        >
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send(input);
              }
            }}
            placeholder="Ask a question about demand, risk, or a recommendation…"
            className="min-h-[44px] resize-none"
          />
          <Button type="submit" disabled={chat.isPending || !input.trim()}>
            Send
          </Button>
        </form>
      </Card>
    </div>
  );
}

export function ChatBubble({ message, pending = false }: { message: ChatMessage; pending?: boolean }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex items-start gap-3", isUser && "flex-row-reverse")}>
      <Avatar>
        <AvatarFallback className={isUser ? "bg-secondary" : "bg-primary/10 text-primary"}>
          {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted",
          pending && "text-muted-foreground italic"
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
