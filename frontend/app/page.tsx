"use client";

import { useState, useEffect, useRef } from "react";
import { useWorkspace } from "@/components/providers/workspace-provider";
import { AnswerBlock } from "@/components/query/answer-block";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { useQueryStream } from "@/hooks/use-query-stream";
import { ScopeSelector } from "@/components/scope-selector";
import { QueryHistory, addQueryToHistory } from "@/components/query/query-history";

export default function SearchPage() {
  // Hooks
  const {
    messages,
    streamStatus,
    startStream,
    reset,
    isTyping
  } = useQueryStream();

  const {
    selectedWorkspace,
    workspaces,
    docs,
    setSelectedWorkspace,
    workspaceCounts
  } = useWorkspace();

  // Local State
  const [query, setQuery] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    // Save to history
    addQueryToHistory(query, selectedWorkspace);

    await startStream(query, selectedWorkspace);
    setQuery("");
  };

  // Helper to format message for AnswerBlock
  const getResultForMessage = (msg: any) => ({
    answer: msg.content,
    sources: msg.sources || [],
    abstained: msg.abstained,
    explanation: msg.explanation,
    closest_mentions: []
  });

  const isStreaming = streamStatus === "streaming";

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm flex-shrink-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">
            D
          </div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Digital Filing Cabinet</h1>
        </div>

        <div className="flex items-center gap-4">
          <ScopeSelector
            workspaces={workspaces}
            selectedWorkspace={selectedWorkspace}
            onSelect={setSelectedWorkspace}
            counts={workspaceCounts}
          />
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="max-w-3xl mx-auto space-y-8 pb-32">

          {/* Empty State */}
          {messages.length === 0 && (
            <>
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-6 opacity-50">
                <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center text-gray-400">
                  <Search className="w-10 h-10" />
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-gray-900">Ready to help</h2>
                  <p className="text-gray-500 mt-2">Ask a question to start a conversation with your documents.</p>
                </div>
              </div>

              <QueryHistory onSelectQuery={(q) => { setQuery(q); }} />
            </>
          )}

          {/* Messages */}
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>

              {/* User Bubble */}
              {msg.role === "user" ? (
                <div className="bg-blue-600 text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[85%] shadow-sm text-base">
                  {msg.content}
                </div>
              ) : (
                /* Assistant Answer Block */
                <div className="w-full">
                  <div className="flex items-center gap-2 mb-2 ml-1">
                    <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center border border-green-200">
                      <div className={`w-2 h-2 rounded-full ${msg.isStreaming ? "bg-green-500 animate-pulse" : "bg-green-600"}`} />
                    </div>
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Assistant</span>
                  </div>

                  <AnswerBlock
                    result={getResultForMessage(msg)}
                    docs={docs}
                    statusMessage={msg.statusMessage}
                    isStreaming={msg.isStreaming}
                    // Only show visual typing for the VERY LAST message if it's strictly the active one
                    isTyping={idx === messages.length - 1 && isTyping}
                  />
                </div>
              )}

            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input Footer */}
      <div className="bg-white border-t p-4 flex-shrink-0 z-20">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSearch} className="relative shadow-lg rounded-xl overflow-hidden border border-gray-200 focus-within:ring-2 ring-blue-500/20 transition-all">
            <Search className="absolute left-4 top-4 h-5 w-5 text-gray-400" />
            <textarea
              className="w-full pl-12 pr-24 py-4 text-lg border-none focus-visible:ring-0 focus:outline-none rounded-none bg-white resize-none min-h-[56px] max-h-[200px] overflow-y-auto"
              placeholder={`Message ${selectedWorkspace}...`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch(e as any);
                }
              }}
              disabled={isStreaming}
              rows={1}
              style={{
                height: 'auto',
                minHeight: '56px'
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = Math.min(target.scrollHeight, 200) + 'px';
              }}
            />
            <div className="absolute right-2 bottom-2">
              {isStreaming ? (
                <Button
                  type="button"
                  onClick={reset} // TODO: Proper cancel
                  variant="ghost"
                  size="sm"
                  className="h-10 px-4 text-red-500 hover:text-red-700 hover:bg-red-50 font-medium"
                >
                  Stop
                </Button>
              ) : (
                <Button
                  type="submit"
                  disabled={!query.trim()}
                  className="h-10 px-6 bg-gray-900 hover:bg-black text-white rounded-lg transition-all"
                >
                  Send
                </Button>
              )}
            </div>
          </form>
          <div className="text-center mt-3">
            <span className="text-[10px] text-gray-400 uppercase tracking-widest">
              Context Aware • {selectedWorkspace}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
