import React from "react";
import { useDispatch } from "react-redux";
import ChatSidebar from "./ChatSidebar";
import FormPanel from "./FormPanel";
import { clearDraft, setIsSaved } from "../store/InteractionSlice";
import { resetChat } from "../store/chatSlice";

export default function LogInteractionScreen() {
  const dispatch = useDispatch();

  const currentDate = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const handleClear = () => {
    dispatch(clearDraft());
    dispatch(setIsSaved(false));
    dispatch(resetChat());
  };

  return (
    <div className="flex flex-col h-screen bg-[#f8fafc] text-slate-900 overflow-hidden font-inter">
      {/* Top Bar */}
      <header className="sticky top-0 flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 z-50 shrink-0">
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

        <div className="flex items-center space-x-3">
          <button 
            onClick={handleClear}
            className="px-3 py-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-transparent hover:border-slate-200"
          >
            Clear Form
          </button>
          <div className="flex items-center space-x-2 bg-indigo-50 px-4 py-2 rounded-xl border border-indigo-100">
            <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-bold text-indigo-700">Log Interaction</span>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <main className="flex-1 overflow-hidden p-4">
        <div className="h-full grid grid-cols-1 lg:grid-cols-[65%_35%] gap-4 lg:w-[calc(100%-1rem)]">
          
          {/* Left Column: Form Panel */}
          <div className="h-full overflow-y-auto bg-white rounded-xl shadow-sm border border-slate-200 pb-[45vh] lg:pb-0">
            <FormPanel />
          </div>

          {/* Right Column: Chat Sidebar */}
          <div className="fixed bottom-0 left-0 right-0 h-[45vh] bg-white border-t border-slate-200 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.2)] z-40 overflow-y-auto lg:relative lg:h-full lg:rounded-xl lg:shadow-sm lg:border lg:border-slate-200 lg:z-auto">
            <ChatSidebar />
          </div>

        </div>
      </main>
    </div>
  );
}
