import React from "react";

export default function MessageBubble({ message, isLoading = false }) {
  if (isLoading) {
    return (
      <div className="flex justify-start mb-4">
        <div className="bg-white border border-gray-200 p-3 rounded-2xl rounded-tl-none shadow-sm">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
          </div>
        </div>
      </div>
    );
  }

  const { role, content, timestamp, toolCalled } = message;
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? "order-2" : "order-1"}`}>
        <div
          className={`p-3 rounded-2xl ${
            isUser
              ? "bg-indigo-600 text-white rounded-tl-none shadow-md"
              : "bg-white border border-gray-200 text-gray-800 rounded-tl-none shadow-sm"
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
          
          {!isUser && toolCalled && (
            <div className="mt-2 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200">
              <span className="mr-1">🔧</span>
              {toolCalled}
            </div>
          )}
        </div>
        
        <div className={`mt-1 px-1 ${isUser ? "text-right" : "text-left"}`}>
          <span className="text-[10px] text-gray-400">
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  );
}
