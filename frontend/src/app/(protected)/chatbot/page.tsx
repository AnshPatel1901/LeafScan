"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bot,
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  MessageSquare,
  Plus,
  Send,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  createChatSession,
  deleteChatDocument,
  deleteChatSession,
  getChatDocuments,
  getChatSession,
  getChatSessions,
  getApiErrorMessage,
  sendChatMessage,
  uploadChatDocument,
} from "@/lib/api";
import type {
  ChatDocument,
  ChatMessage,
  ChatSession,
  SourceCitation,
} from "@/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDate(iso: string) {
  const d = new Date(iso);
  const today = new Date();
  const diff = today.getDate() - d.getDate();
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function SourcesAccordion({ sources }: { sources: SourceCitation[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-2 text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
      >
        {open ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        {sources.length} source{sources.length > 1 ? "s" : ""}
      </button>
      {open && (
        <div className="mt-1.5 space-y-1.5 pl-4">
          {sources.map((s, i) => (
            <div key={i} className="bg-[var(--bg-subtle)] rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-0.5">
                <FileText className="w-3 h-3 text-[var(--green)] flex-shrink-0" />
                <span className="font-medium text-[var(--text)] truncate">
                  {s.source}
                </span>
                {s.page != null && (
                  <span className="text-[var(--text-muted)] flex-shrink-0">
                    · p.{s.page + 1}
                  </span>
                )}
              </div>
              {s.preview && (
                <p className="text-[var(--text-muted)] line-clamp-2 leading-relaxed">
                  {s.preview}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs font-bold mt-0.5
          ${
            isUser
              ? "bg-[var(--green)] dark:bg-[var(--green-dark)]"
              : "bg-[var(--bg-subtle)] border border-[var(--border)]"
          }`}
      >
        {isUser ? "U" : <Bot className="w-3.5 h-3.5 text-[var(--green)]" />}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}
      >
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
            ${
              isUser
                ? "bg-[var(--green)] dark:bg-[var(--green-dark)] text-white rounded-tr-sm"
                : "bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text)] rounded-tl-sm"
            }`}
        >
          {msg.content}
        </div>
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <SourcesAccordion sources={msg.sources} />
        )}
        <span className="text-[10px] text-[var(--text-muted)] px-1">
          {formatTime(msg.created_at)}
        </span>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center bg-[var(--bg-subtle)] border border-[var(--border)] mt-0.5">
        <Bot className="w-3.5 h-3.5 text-[var(--green)]" />
      </div>
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[var(--green-light)] flex items-center justify-center">
        <MessageSquare className="w-8 h-8 text-[var(--green)]" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-[var(--text)] mb-1">
          Ask your knowledge base
        </h2>
        <p className="text-sm text-[var(--text-muted)] max-w-xs">
          Upload PDFs and ask questions. Answers come from your documents, not
          the internet.
        </p>
      </div>
      <button
        onClick={onNew}
        className="flex items-center gap-2 px-4 py-2 bg-[var(--green)] hover:bg-[var(--green-dark,var(--green))] text-white rounded-xl text-sm font-medium transition-colors"
      >
        <Plus className="w-4 h-4" />
        New Chat
      </button>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function ChatbotPage() {
  // ── Sessions sidebar state ──────────────────────────────────────────────────
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);

  // ── Documents state ─────────────────────────────────────────────────────────
  const [documents, setDocuments] = useState<ChatDocument[]>([]);
  const [docsOpen, setDocsOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  // ── Chat input state ────────────────────────────────────────────────────────
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  // ── Refs ────────────────────────────────────────────────────────────────────
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Scroll to bottom on new messages ───────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // ── Auto-resize textarea ────────────────────────────────────────────────────
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [input]);

  // ── Load sessions on mount ──────────────────────────────────────────────────
  useEffect(() => {
    loadSessions();
    loadDocuments();
  }, []);

  // ── Load messages when active session changes ───────────────────────────────
  useEffect(() => {
    if (activeSessionId) loadMessages(activeSessionId);
    else setMessages([]);
  }, [activeSessionId]);

  // ── Data fetching ───────────────────────────────────────────────────────────

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const list = await getChatSessions();
      setSessions(list);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Failed to load chat sessions"));
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const loadMessages = useCallback(async (sessionId: string) => {
    setMessagesLoading(true);
    try {
      const detail = await getChatSession(sessionId);
      setMessages(detail.messages);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Failed to load messages"));
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await getChatDocuments();
      setDocuments(docs);
    } catch {
      // non-critical — silently ignore
    }
  }, []);

  // ── Actions ─────────────────────────────────────────────────────────────────

  const handleNewSession = useCallback(async () => {
    try {
      const session = await createChatSession("New Chat");
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Failed to create session"));
    }
  }, []);

  const handleSelectSession = useCallback(
    (id: string) => {
      if (id === activeSessionId) return;
      setActiveSessionId(id);
    },
    [activeSessionId],
  );

  const handleDeleteSession = useCallback(
    async (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      try {
        await deleteChatSession(id);
        setSessions((prev) => prev.filter((s) => s.id !== id));
        if (activeSessionId === id) {
          setActiveSessionId(null);
          setMessages([]);
        }
        toast.success("Session deleted");
      } catch (err) {
        toast.error(getApiErrorMessage(err, "Failed to delete session"));
      }
    },
    [activeSessionId],
  );

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    // Auto-create a session if none selected
    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await createChatSession("New Chat");
        setSessions((prev) => [session, ...prev]);
        setActiveSessionId(session.id);
        sessionId = session.id;
      } catch (err) {
        toast.error(getApiErrorMessage(err, "Failed to create session"));
        return;
      }
    }

    setInput("");
    setSending(true);

    // Optimistically add the user message for instant feedback
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: sessionId,
      role: "user",
      content: text,
      sources: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const resp = await sendChatMessage(sessionId, text);

      // Replace temp message + add assistant reply
      setMessages((prev) => {
        const without = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...without, resp.user_message, resp.assistant_message];
      });

      // Update session title in the sidebar
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                title: text.slice(0, 60) + (text.length > 60 ? "…" : ""),
                updated_at: new Date().toISOString(),
                message_count: s.message_count + 2,
              }
            : s,
        ),
      );
    } catch (err) {
      // Remove the optimistic user message on failure
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
      toast.error(
        getApiErrorMessage(err, "Failed to send message. Please try again."),
      );
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  }, [input, sending, activeSessionId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDocumentUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Only PDF files are accepted");
        return;
      }
      setUploading(true);
      try {
        const result = await uploadChatDocument(file);
        if (result.already_indexed) {
          toast("Document was already in the knowledge base", { icon: "ℹ️" });
        } else {
          toast.success(
            `Indexed "${result.document.name}" — ${result.document.pages} pages, ${result.document.chunks} chunks`,
          );
        }
        await loadDocuments();
      } catch (err) {
        toast.error(getApiErrorMessage(err, "Failed to upload document"));
      } finally {
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    [loadDocuments],
  );

  const handleDeleteDocument = useCallback(
    async (docId: string, docName: string) => {
      try {
        await deleteChatDocument(docId);
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
        toast.success(`"${docName}" removed from knowledge base`);
      } catch (err) {
        toast.error(getApiErrorMessage(err, "Failed to delete document"));
      }
    },
    [],
  );

  // ── Render ──────────────────────────────────────────────────────────────────

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Left sessions panel ── */}
      <aside className="w-60 flex-shrink-0 flex flex-col border-r border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-3 border-b border-[var(--border)]">
          <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
            Chats
          </span>
          <button
            onClick={handleNewSession}
            title="New chat"
            className="w-6 h-6 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--green)] transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto py-1 min-h-0">
          {sessionsLoading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="w-4 h-4 animate-spin text-[var(--text-muted)]" />
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)] text-center py-6 px-3">
              No conversations yet.{" "}
              <button
                onClick={handleNewSession}
                className="underline hover:text-[var(--green)]"
              >
                Start one
              </button>
            </p>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                role="button"
                tabIndex={0}
                onClick={() => handleSelectSession(s.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectSession(s.id);
                  }
                }}
                className={`group w-full flex items-start gap-2 px-3 py-2 text-left rounded-lg mx-1 transition-all duration-100 cursor-pointer
                  ${
                    s.id === activeSessionId
                      ? "bg-[var(--green-light)] text-[var(--green)] dark:text-[var(--green-dark)]"
                      : "text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text)]"
                  }`}
                style={{ width: "calc(100% - 8px)" }}
              >
                <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate leading-snug">
                    {s.title}
                  </p>
                  <p className="text-[10px] opacity-60 mt-0.5">
                    {formatDate(s.updated_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSession(e, s.id);
                  }}
                  title="Delete session"
                  className="opacity-0 group-hover:opacity-100 w-4 h-4 flex items-center justify-center hover:text-red-500 transition-all flex-shrink-0 mt-0.5"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Documents section */}
        <div className="border-t border-[var(--border)]">
          <button
            onClick={() => setDocsOpen(!docsOpen)}
            className="w-full flex items-center justify-between px-3 py-2.5 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide hover:text-[var(--text)] transition-colors"
          >
            <span>Knowledge Base ({documents.length})</span>
            {docsOpen ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
          </button>

          {docsOpen && (
            <div className="pb-2">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="group flex items-center gap-2 px-3 py-1.5 hover:bg-[var(--bg-subtle)] transition-colors mx-1 rounded-lg"
                >
                  <FileText className="w-3.5 h-3.5 text-[var(--green)] flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[var(--text)] truncate">
                      {doc.name}
                    </p>
                    <p className="text-[10px] text-[var(--text-muted)]">
                      {doc.pages}p · {doc.chunks} chunks
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteDocument(doc.id, doc.name)}
                    title="Remove document"
                    className="opacity-0 group-hover:opacity-100 hover:text-red-500 transition-all flex-shrink-0"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}

              <div className="px-3 pt-1">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 text-xs text-[var(--text-muted)] border border-dashed border-[var(--border)] rounded-lg hover:border-[var(--green)] hover:text-[var(--green)] transition-colors disabled:opacity-50"
                >
                  {uploading ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Upload className="w-3 h-3" />
                  )}
                  {uploading ? "Indexing…" : "Upload PDF"}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={handleDocumentUpload}
                />
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ── Right chat panel ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top bar */}
        {activeSession && (
          <div className="flex items-center gap-3 px-6 py-3 border-b border-[var(--border)] bg-[var(--bg-card)]">
            <MessageSquare className="w-4 h-4 text-[var(--green)] flex-shrink-0" />
            <h1 className="text-sm font-medium text-[var(--text)] truncate">
              {activeSession.title}
            </h1>
            <span className="ml-auto text-xs text-[var(--text-muted)] flex-shrink-0">
              {activeSession.message_count} msg
              {activeSession.message_count !== 1 ? "s" : ""}
            </span>
          </div>
        )}

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
          {!activeSessionId ? (
            <EmptyState onNew={handleNewSession} />
          ) : messagesLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-[var(--text-muted)]" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-center py-12">
              <Bot className="w-10 h-10 text-[var(--text-muted)]" />
              <p className="text-sm text-[var(--text-muted)] max-w-xs">
                Ask a question about your uploaded documents. Answers are
                grounded in the knowledge base only.
              </p>
              {documents.length === 0 && (
                <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-1.5 rounded-lg">
                  No documents indexed yet — upload a PDF first.
                </p>
              )}
            </div>
          ) : (
            messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)
          )}
          {sending && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-[var(--border)] bg-[var(--bg-card)] px-4 py-3">
          {documents.length === 0 && (
            <div className="flex items-center gap-2 mb-2 text-xs text-amber-600 dark:text-amber-400">
              <Upload className="w-3 h-3 flex-shrink-0" />
              <span>
                Knowledge base is empty.{" "}
                <button
                  className="underline hover:no-underline"
                  onClick={() => {
                    setDocsOpen(true);
                    fileInputRef.current?.click();
                  }}
                >
                  Upload a PDF
                </button>{" "}
                to start chatting.
              </span>
            </div>
          )}
          <div className="flex items-end gap-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                documents.length === 0
                  ? "Upload a PDF to enable chat…"
                  : "Ask a question… (Enter to send, Shift+Enter for newline)"
              }
              disabled={sending}
              rows={1}
              className={`flex-1 resize-none bg-[var(--bg-subtle)] border border-[var(--border)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--green)] focus:border-transparent transition-all overflow-hidden leading-relaxed
                ${sending ? "opacity-60 cursor-not-allowed" : ""}`}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-xl bg-[var(--green)] text-white hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
              title="Send (Enter)"
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-[10px] text-[var(--text-muted)] mt-1.5 text-right">
            Answers are grounded in uploaded documents only.
          </p>
        </div>
      </div>
    </div>
  );
}
