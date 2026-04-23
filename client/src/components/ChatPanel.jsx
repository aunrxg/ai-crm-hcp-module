import React, { useState, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { addMessage, setLoading, setError, initSession } from "../store/chatSlice";
import { updateDraft, setIsSaved, setLastSavedId } from "../store/InteractionSlice";
import { sendMessage } from "../api/client";
import MessageBubble from "./MessageBubble";

const SUGGESTED_PROMPTS = [
  "Log my visit with Dr. Sharma today",
  "Tell me about this HCP before I go in",
  "Schedule a follow-up for next Monday",
  "Analyze my recent visits with this doctor",
  "Change the sentiment to positive",
];

export default function ChatPanel() {
  const dispatch = useDispatch();
  const messagesEndRef = useRef(null);
  const [inputText, setInputText] = useState("");

  const { messages, loading, sessionId } = useSelector((state) => state.chat);
  const { selectedHCP } = useSelector((state) => state.hcp);
  const { draft } = useSelector((state) => state.interaction);

  // Initialize session on mount
  useEffect(() => {
    dispatch(initSession());
  }, [dispatch]);

  // Scroll to bottom when messages change or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (text = inputText) => {
    const trimmedText = text.trim();
    if (!trimmedText || loading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: trimmedText,
      timestamp: new Date().toISOString(),
    };

    dispatch(addMessage(userMessage));
    setInputText("");
    dispatch(setLoading(true));
    dispatch(setError(null));

    try {
      const response = await sendMessage(
        trimmedText,
        sessionId,
        selectedHCP?.id,
        selectedHCP?.name,
        draft,
        messages
      );

      const { response: assistantContent, tool_called, interaction_draft } = response.data;

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: assistantContent,
        timestamp: new Date().toISOString(),
        toolCalled: tool_called,
      };

      dispatch(addMessage(assistantMessage));
      
      if (interaction_draft) {
        dispatch(updateDraft(interaction_draft));
        
        // Final wiring check (Point 6)
        if (tool_called === "log_interaction") {
          dispatch(setIsSaved(true));
          dispatch(setLastSavedId(response.data.interaction_id));
        } else if (tool_called === "edit_interaction") {
          // Fields are updated via updateDraft(interaction_draft)
          dispatch(setIsSaved(false)); // or keep true if it was already saved? 
          // Usually an edit to a saved interaction should probably show a "updated" status.
        }
      }
    } catch (err) {
      console.error("Chat error:", err);
      dispatch(setError("Failed to send message. Please try again."));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200 shadow-xl overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
            <span className="text-xl">🤖</span>
          </div>
          <div>
            <h2 className="font-semibold text-gray-900 leading-tight">AI Assistant</h2>
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              <span className="text-xs text-gray-500 font-medium">Online</span>
            </div>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <main className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <div className="bg-indigo-50 p-4 rounded-full">
              <span className="text-3xl">👋</span>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">How can I help you today?</h3>
              <p className="text-sm text-gray-500 mt-1">Try one of these suggestions to get started:</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 max-w-md">
              {SUGGESTED_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt)}
                  className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:border-indigo-400 hover:text-indigo-600 transition-all shadow-sm hover:shadow-md"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {loading && <MessageBubble isLoading={true} />}
            <div ref={messagesEndRef} />
          </>
        )}
      </main>

      {/* Input Area */}
      <footer className="p-6 bg-white border-t border-gray-200">
        <div className="relative group">
          <textarea
            rows="2"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={loading ? "Waiting for response..." : "Type your message here..."}
            disabled={loading}
            className="w-full pl-4 pr-16 py-3 border border-gray-200 rounded-2xl bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all resize-none text-sm placeholder:text-gray-400"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !inputText.trim()}
            className={`absolute right-2 bottom-2 p-2.5 rounded-xl transition-all ${
              loading || !inputText.trim()
                ? "bg-gray-100 text-gray-400"
                : "bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg hover:shadow-indigo-200 active:scale-95"
            }`}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 rotate-90"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
        <p className="mt-2 text-center text-[10px] text-gray-400">
          Tip: Press Enter to send, Shift + Enter for a new line.
        </p>
      </footer>
    </div>
  );
}
