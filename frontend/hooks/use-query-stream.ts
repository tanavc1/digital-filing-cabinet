/**
 * useQueryStream Hook
 * -------------------
 * Manages the chat interaction loop:
 * 1. Sends user message + history to backend SSE endpoint.
 * 2. Processes incoming SSE events (token, sources, status, error).
 * 3. Handles "Typewriter" effect for smooth assistant text rendering.
 * 4. Manages errors via Sonner toasts.
 */
import { useState, useCallback, useRef } from "react";
import { Evidence } from "@/lib/types";
import { toast } from "sonner";

// Helper to parse SSE lines
const parseSSELine = (line: string): any | null => {
    if (!line.startsWith("data: ")) return null;
    try {
        return JSON.parse(line.substring(6));
    } catch (e) {
        console.error("Failed to parse SSE JSON:", e);
        return null;
    }
};

export type StreamStatus = "idle" | "streaming" | "done" | "error";

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    sources?: Evidence[]; // Only for assistant
    statusMessage?: string; // Only for assistant (during stream)
    isStreaming?: boolean;
    abstained?: boolean;
    explanation?: string;
}

interface UseQueryStreamResult {
    messages: ChatMessage[];
    streamStatus: StreamStatus;
    startStream: (q: string, workspaceId: string) => Promise<void>;
    reset: () => void;
    isTyping: boolean;
}

export function useQueryStream(): UseQueryStreamResult {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [streamStatus, setStreamStatus] = useState<StreamStatus>("idle");
    const [isTyping, setIsTyping] = useState(false);

    // Typewriter buffer state
    const targetAnswerRef = useRef("");
    const currentAnswerRef = useRef("");
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    const abortRef = useRef<AbortController | null>(null);
    const activeStreamId = useRef<number>(0);
    const streamDoneRef = useRef(false);

    const reset = useCallback(() => {
        setMessages([]);
        setStreamStatus("idle");
        setIsTyping(false);
        targetAnswerRef.current = "";
        currentAnswerRef.current = "";
        if (timerRef.current) clearInterval(timerRef.current);
        if (abortRef.current) abortRef.current.abort();
    }, []);

    // Update the last assistant message in the list
    const updateLastMessage = (update: Partial<ChatMessage>) => {
        setMessages(prev => {
            const last = prev[prev.length - 1];
            if (!last || last.role !== "assistant") return prev;
            return [...prev.slice(0, -1), { ...last, ...update }];
        });
    };

    // Typewriter Loop
    const startTypewriter = useCallback(() => {
        if (timerRef.current) clearInterval(timerRef.current);
        setIsTyping(true);

        timerRef.current = setInterval(() => {
            const current = currentAnswerRef.current;
            const target = targetAnswerRef.current;

            if (current.length < target.length) {
                const nextChar = target[current.length];
                currentAnswerRef.current += nextChar;
                // Update UI with partial answer
                updateLastMessage({ content: currentAnswerRef.current });
            } else {
                if (streamDoneRef.current) {
                    // Turn off visual typing only when stream fully done
                    setIsTyping(false);
                    updateLastMessage({ isStreaming: false });
                    if (timerRef.current) clearInterval(timerRef.current);
                }
            }
        }, 20);
    }, []);

    const startStream = useCallback(async (q: string, workspaceId: string) => {
        const streamId = Date.now();
        activeStreamId.current = streamId;
        streamDoneRef.current = false;

        // Abort previous stream and reset state
        if (abortRef.current) abortRef.current.abort();
        if (timerRef.current) clearInterval(timerRef.current);
        setIsTyping(false); // Ensure typing is off before new stream starts

        // 1. Add User Message
        const newMsg: ChatMessage = { role: "user", content: q };

        // 2. Add Placeholder Assistant Message
        const pendingMsg: ChatMessage = {
            role: "assistant",
            content: "",
            statusMessage: "Initializing...",
            isStreaming: true
        };

        // We must calculate the history to send BEFORE adding the placeholder
        // Actually, React state updates are async, so 'messages' is old here.
        // We need to use functional update but we also need the value for API.
        // Better to maintain a ref for history or just pass what we know.
        // Constraint: We need to send [prevMsgs..., userMsg].

        let historyToSend: any[] = [];
        setMessages(prev => {
            historyToSend = prev.map(m => ({ role: m.role, content: m.content }));
            historyToSend.push({ role: "user", content: q });
            return [...prev, newMsg, pendingMsg];
        });

        setStreamStatus("streaming");

        // Reset buffers for THIS new answer
        targetAnswerRef.current = "";
        currentAnswerRef.current = "";
        startTypewriter();

        const controller = new AbortController();
        abortRef.current = controller;

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

            const response = await fetch(`${API_URL}/query_stream`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": process.env.NEXT_PUBLIC_API_SECRET || ""
                },
                body: JSON.stringify({
                    q,
                    workspace_id: workspaceId,
                    messages: historyToSend
                }),
                signal: controller.signal,
            });

            if (!response.ok || !response.body) throw new Error(response.statusText);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                if (activeStreamId.current !== streamId) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                const lines = buffer.split("\n\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (activeStreamId.current !== streamId) break;
                    const event = parseSSELine(line);
                    if (!event) continue;

                    switch (event.type) {
                        case "status":
                            updateLastMessage({ statusMessage: event.msg });
                            break;
                        case "sources":
                            updateLastMessage({ sources: event.data });
                            break;
                        case "token":
                            targetAnswerRef.current += event.text;
                            break;
                        case "abstained":
                            // Update explanation
                            updateLastMessage({
                                abstained: true,
                                explanation: event.explanation,
                                statusMessage: undefined, // Clear status
                                isStreaming: false
                            });
                            setIsTyping(false);
                            break;
                        case "done":
                            setStreamStatus("done");
                            updateLastMessage({ statusMessage: undefined }); // Clear status
                            streamDoneRef.current = true;
                            break;
                        case "error":
                            console.error("Stream Error:", event.msg);
                            setStreamStatus("error");
                            updateLastMessage({
                                statusMessage: `Error: ${event.msg}`,
                                isStreaming: false
                            });
                            toast.error("Stream Error", { description: event.msg });
                            setIsTyping(false);
                            break;
                    }
                }
            }
        } catch (error: any) {
            if (activeStreamId.current !== streamId) return;

            if (error.name === "AbortError") {
                console.log("Stream aborted");
            } else {
                console.error("Stream fetch error:", error);
                setStreamStatus("error");
                updateLastMessage({ statusMessage: "Network error.", isStreaming: false });
                toast.error("Network Error", {
                    description: error.message || "Failed to connect to backend."
                });
            }
            setIsTyping(false);
        }
    }, [startTypewriter]);

    return {
        messages,
        streamStatus,
        startStream,
        reset,
        isTyping
    };
}
