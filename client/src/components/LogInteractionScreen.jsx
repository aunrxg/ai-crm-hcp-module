import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import ChatPanel from "./ChatPanel";
import FormPanel from "./FormPanel";
import HCPSelector from "./HCPSelector";

export default function LogInteractionScreen() {
  const dispatch = useDispatch();
  const messages = useSelector((state) => state.chat.messages);
  const [showHint, setShowHint] = useState(true);

  // Dismiss hint after the first user message
  useEffect(() => {
    if (messages.length > 0 && showHint) {
      setShowHint(false);
    }
  }, [messages, showHint]);

  const currentDate = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="flex flex-col h-screen bg-slate-50 text-slate-900 overflow-hidden font-inter">
      {/* Top Bar */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 z-20">
        <div className="flex items-center space-x-4">
          <div className="bg-indigo-600 p-2 rounded-lg shadow-lg shadow-indigo-200">
            <svg
              className="w-5 h-5 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-extrabold text-slate-900 leading-none">CRM HCP</h1>
            <p className="text-[10px] text-slate-400 uppercase font-black tracking-widest mt-0.5">
              Medical Intelligence
            </p>
          </div>
        </div>

        <div className="hidden md:block text-center">
          <span className="px-4 py-1.5 bg-slate-100 rounded-full text-xs font-bold text-slate-600 border border-slate-200">
            {currentDate}
          </span>
        </div>

        <div className="flex items-center space-x-2 bg-indigo-50 px-4 py-2 rounded-xl border border-indigo-100">
          <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse"></div>
          <span className="text-sm font-bold text-indigo-700">Log Interaction</span>
        </div>
      </header>

      {/* Selector Area */}
      <div className="bg-white px-6 py-4 border-b border-slate-200 shadow-sm z-10">
        <HCPSelector />
        
        {showHint && (
          <div className="mt-4 flex items-center space-x-2 bg-indigo-50 px-4 py-2.5 rounded-xl border border-indigo-100 text-indigo-700 text-sm animate-in slide-in-from-top duration-500">
            <span className="text-lg">💬</span>
            <p className="font-medium">
              Use the chat on the left to log interactions. The form on the right updates automatically.
            </p>
            <button 
              onClick={() => setShowHint(false)}
              className="ml-auto text-indigo-400 hover:text-indigo-600 transition-colors"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Main Split Layout */}
      <main className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
        {/* Left: Form Panel */}
        <div className="w-full md:w-1/2 h-full bg-slate-50 border-t md:border-t-0 md:border-l border-slate-200 overflow-hidden">
          <FormPanel />
        </div>

        {/* Divider */}
        {/* <div className="hidden md:flex absolute left-1/2 top-0 bottom-0 w-px bg-slate-200 z-10 items-center justify-center">
          <div className="bg-white border border-slate-200 p-1.5 rounded-full shadow-sm text-slate-400">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7h8m0 0l-4-4m4 4l-4 4m0 6H8m0 0l4 4m-4-4l4-4"
              />
            </svg>
          </div>
        </div> */}

        {/* Right: Chat Panel */}
        <div className="w-full md:w-1/2 h-full bg-white relative z-0">
          <ChatPanel />
        </div>
      </main>
    </div>
  );
}
