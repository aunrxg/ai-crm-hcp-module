import React, { useState, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { addMessage, setLoading, setError, initSession } from "../store/chatSlice";
import { updateDraft, setIsSaved } from "../store/InteractionSlice";
import { sendMessage } from "../api/client";

export default function ChatSidebar() {
  const dispatch = useDispatch();
  const messagesEndRef = useRef(null);
  const [inputText, setInputText] = useState("");

  const { messages, loading, sessionId, error } = useSelector((state) => state.chat);
  const { draft } = useSelector((state) => state.interaction);

  useEffect(() => {
    dispatch(initSession());
  }, [dispatch]);

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
        draft.hcp_id,
        draft.hcp_name,
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
        if (tool_called === "log_interaction") {
          dispatch(setIsSaved(true));
        } else if (tool_called === "edit_interaction") {
          dispatch(setIsSaved(false));
        }
      }
    } catch (err) {
      console.error("Chat error:", err);
      dispatch(setError("Connection error, please retry"));
      setTimeout(() => dispatch(setError(null)), 5000);
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
    <div className="flex flex-col h-full bg-white rounded-xl shadow-sm overflow-hidden font-inter border border-slate-200">
      {/* Header */}
      <header className="flex items-center px-4 py-3 border-b border-slate-200 shrink-0">
        <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-xs mr-3 shrink-0">
          AI
        </div>
        <div>
          <div className="flex items-center">
            <h2 className="font-semibold text-slate-900 text-sm leading-tight">AI Assistant</h2>
            <span className="w-2 h-2 rounded-full bg-green-500 ml-2"></span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">Log interaction via chat</p>
        </div>
      </header>

      {/* Error Toast */}
      {error && (
        <div className="bg-red-50 text-red-600 px-4 py-2 text-xs border-b border-red-100 flex items-center space-x-2 shrink-0">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Messages Area */}
      <main className="flex-1 overflow-y-auto p-4 space-y-4 bg-white scrollbar-thin scrollbar-thumb-slate-200">
        {messages.length === 0 ? (
          <div className="flex justify-start">
            <div className="bg-slate-50 border border-slate-200 text-slate-500 rounded-tr-2xl rounded-b-2xl rounded-bl-sm text-sm px-4 py-3 max-w-[85%] shadow-sm">
              Log interaction details here (e.g., 'Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure') or ask for help.
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className="max-w-[85%] flex flex-col">
                <div 
                  className={`text-sm px-4 py-3 shadow-sm ${
                    msg.role === "user" 
                      ? "bg-indigo-600 text-white rounded-tl-2xl rounded-b-2xl rounded-br-sm" 
                      : "bg-white border border-slate-200 text-slate-800 rounded-tr-2xl rounded-b-2xl rounded-bl-sm"
                  }`}
                >
                  {msg.content}
                </div>
                {msg.toolCalled && (
                  <div className="mt-1 flex justify-start">
                    <span className="inline-block px-2 py-0.5 bg-slate-100 text-slate-500 text-[10px] font-medium rounded-full border border-slate-200">
                      🔧 {msg.toolCalled}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 rounded-tr-2xl rounded-b-2xl rounded-bl-sm px-4 py-3 shadow-sm flex items-center space-x-1">
              <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="bg-white pt-3 shrink-0">
        <div className="flex border border-slate-300 rounded-lg overflow-hidden mx-3 mb-3 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent transition-all">
          <textarea
            rows="1"
            className="flex-1 bg-slate-50 px-3 py-2 text-sm focus:outline-none placeholder:text-slate-400 resize-none flex items-center pt-[9px]"
            placeholder="Describe interaction..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !inputText.trim()}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              loading || !inputText.trim() ? "bg-slate-100 text-slate-400" : "bg-indigo-600 text-white hover:bg-indigo-700"
            }`}
          >
            Log
          </button>
        </div>
      </footer>
    </div>
  );
}
