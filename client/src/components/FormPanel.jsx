import React from "react";
import { useSelector } from "react-redux";

const TooltipWrapper = ({ children }) => (
  <div className="relative group cursor-help">
    {children}
    <div className="absolute z-10 bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
      Update via chat →
    </div>
  </div>
);

const Section = ({ title, children }) => (
  <section className="mb-8 last:mb-0">
    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
      {title}
    </h3>
    {children}
  </section>
);

const Badge = ({ children, colorClass = "bg-gray-100 text-gray-600" }) => (
  <span className={`px-2 py-1 rounded-full text-xs font-medium ${colorClass} transition-all duration-300`}>
    {children}
  </span>
);

const Placeholder = ({ text = "Not specified" }) => (
  <span className="text-gray-300 italic text-sm">{text}</span>
);

export default function FormPanel() {
  const { draft, isSaved, lastSavedId } = useSelector((state) => state.interaction);

  const sentimentColors = {
    positive: "bg-green-100 text-green-700",
    neutral: "bg-gray-100 text-gray-600",
    negative: "bg-red-100 text-red-700",
  };

  const entities = typeof draft.entities_json === "string" 
    ? JSON.parse(draft.entities_json || "{}") 
    : (draft.entities_json || {});

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden shadow-inner">
      {/* Save Banner */}
      {isSaved && (
        <div className="bg-green-50 border-b border-green-100 px-6 py-3 flex items-center justify-between animate-in fade-in slide-in-from-top duration-500">
          <div className="flex items-center space-x-2 text-green-700">
            <span className="text-lg">✓</span>
            <span className="text-sm font-medium">Interaction saved to database</span>
          </div>
          <span className="text-[10px] bg-green-100 text-green-600 px-2 py-0.5 rounded font-mono uppercase tracking-tighter">
            ID: {lastSavedId || "N/A"}
          </span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
        {/* Section 1: Interaction Details */}
        <Section title="Interaction Details">
          <div className="grid grid-cols-2 gap-6">
            <TooltipWrapper>
              <div className="bg-gray-50 rounded-xl p-4 transition-all hover:bg-gray-100/50">
                <p className="text-[10px] text-gray-400 mb-1 uppercase font-bold">Type</p>
                <div className="flex items-center space-x-2">
                  <span className="text-lg">
                    {draft.interaction_type === "visit" ? "🤝" : 
                     draft.interaction_type === "call" ? "📞" : 
                     draft.interaction_type === "email" ? "✉️" : "📝"}
                  </span>
                  <span className="font-semibold text-gray-800 capitalize">
                    {draft.interaction_type || <Placeholder />}
                  </span>
                </div>
              </div>
            </TooltipWrapper>

            <TooltipWrapper>
              <div className="bg-gray-50 rounded-xl p-4 transition-all hover:bg-gray-100/50">
                <p className="text-[10px] text-gray-400 mb-1 uppercase font-bold">Date & Duration</p>
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-gray-800">
                    {draft.date || <Placeholder text="Date TBD" />}
                  </span>
                  <span className="text-xs text-gray-500">
                    {draft.duration_minutes ? `${draft.duration_minutes} minutes` : <Placeholder text="Duration TBD" />}
                  </span>
                </div>
              </div>
            </TooltipWrapper>

            <TooltipWrapper>
              <div className="bg-gray-50 rounded-xl p-4 transition-all hover:bg-gray-100/50">
                <p className="text-[10px] text-gray-400 mb-1 uppercase font-bold">Sentiment</p>
                <div className="mt-1">
                  {draft.sentiment ? (
                    <Badge colorClass={sentimentColors[draft.sentiment.toLowerCase()]}>
                      {draft.sentiment.toUpperCase()}
                    </Badge>
                  ) : (
                    <Placeholder />
                  )}
                </div>
              </div>
            </TooltipWrapper>

            <TooltipWrapper>
              <div className="bg-gray-50 rounded-xl p-4 transition-all hover:bg-gray-100/50">
                <p className="text-[10px] text-gray-400 mb-1 uppercase font-bold">Status</p>
                <div className="mt-1">
                  <Badge colorClass={isSaved ? "bg-blue-100 text-blue-700" : "bg-amber-100 text-amber-700"}>
                    {isSaved ? "SYNCED" : "DRAFT"}
                  </Badge>
                </div>
              </div>
            </TooltipWrapper>
          </div>
        </Section>

        {/* Section 2: Products Discussed */}
        <Section title="Products Discussed">
          <TooltipWrapper>
            <div className="flex flex-wrap gap-2 min-h-[40px] p-2 rounded-xl transition-all hover:bg-gray-50">
              {draft.products_discussed?.length > 0 ? (
                draft.products_discussed.map((product, i) => (
                  <span key={i} className="px-3 py-1 rounded-full text-sm font-medium border border-indigo-200 text-indigo-600 bg-indigo-50/30 animate-in zoom-in duration-300">
                    {product}
                  </span>
                ))
              ) : (
                <Placeholder text="No products mentioned yet" />
              )}
            </div>
          </TooltipWrapper>
        </Section>

        {/* Section 3: AI Summary */}
        <Section title="AI-Generated Summary">
          <TooltipWrapper>
            <div className="relative overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm transition-all hover:shadow-md">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-500"></div>
              <div className="p-5">
                {draft.ai_summary ? (
                  <p className="text-sm text-gray-700 leading-relaxed animate-in fade-in slide-in-from-left duration-500">
                    {draft.ai_summary}
                  </p>
                ) : (
                  <Placeholder text="Summary will appear after logging the interaction." />
                )}
              </div>
            </div>
          </TooltipWrapper>
        </Section>

        {/* Section 4: Extracted Entities */}
        <Section title="Extracted Entities">
          <div className="space-y-6">
            <TooltipWrapper>
              <div className="p-3 rounded-xl hover:bg-gray-50 transition-colors">
                <p className="text-[10px] text-gray-400 mb-2 uppercase font-bold flex items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 mr-1.5"></span>
                  Drugs Mentioned
                </p>
                <div className="flex flex-wrap gap-2">
                  {entities.drugs_mentioned?.length > 0 ? (
                    entities.drugs_mentioned.map((d, i) => <Badge key={i} colorClass="bg-green-50 text-green-700 border border-green-100">{d}</Badge>)
                  ) : <Placeholder />}
                </div>
              </div>
            </TooltipWrapper>

            <TooltipWrapper>
              <div className="p-3 rounded-xl hover:bg-gray-50 transition-colors">
                <p className="text-[10px] text-gray-400 mb-2 uppercase font-bold flex items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 mr-1.5"></span>
                  Objections Raised
                </p>
                <div className="flex flex-wrap gap-2">
                  {entities.objections?.length > 0 ? (
                    entities.objections.map((o, i) => <Badge key={i} colorClass="bg-red-50 text-red-700 border border-red-100">{o}</Badge>)
                  ) : <Placeholder />}
                </div>
              </div>
            </TooltipWrapper>

            <TooltipWrapper>
              <div className="p-3 rounded-xl hover:bg-gray-50 transition-colors">
                <p className="text-[10px] text-gray-400 mb-2 uppercase font-bold flex items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mr-1.5"></span>
                  Competitors
                </p>
                <div className="flex flex-wrap gap-2">
                  {entities.competitors?.length > 0 ? (
                    entities.competitors.map((c, i) => <Badge key={i} colorClass="bg-amber-50 text-amber-700 border border-amber-100">{c}</Badge>)
                  ) : <Placeholder />}
                </div>
              </div>
            </TooltipWrapper>

            <TooltipWrapper>
              <div className="p-3 rounded-xl hover:bg-gray-50 transition-colors">
                <p className="text-[10px] text-gray-400 mb-2 uppercase font-bold flex items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 mr-1.5"></span>
                  Action Items
                </p>
                <div className="space-y-1">
                  {entities.action_items?.length > 0 ? (
                    entities.action_items.map((a, i) => (
                      <p key={i} className="text-sm text-gray-600 flex items-start">
                        <span className="mr-2 mt-1.5 w-1 h-1 rounded-full bg-gray-300 shrink-0"></span>
                        {a}
                      </p>
                    ))
                  ) : <Placeholder />}
                </div>
              </div>
            </TooltipWrapper>
          </div>
        </Section>

        {/* Section 5: Follow-up */}
        <Section title="Follow-up Plan">
          <TooltipWrapper>
            {draft.follow_up_date || draft.follow_up_task ? (
              <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl p-5 text-white shadow-lg animate-in zoom-in duration-500">
                <div className="flex items-start justify-between mb-4">
                  <div className="bg-white/20 p-2 rounded-xl backdrop-blur-sm">
                    <span className="text-xl">📅</span>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-indigo-100 uppercase font-bold">Due Date</p>
                    <p className="font-semibold">{draft.follow_up_date || "No date set"}</p>
                  </div>
                </div>
                <p className="text-sm text-indigo-50 font-medium leading-relaxed italic">
                  "{draft.follow_up_task || "No task description provided"}"
                </p>
              </div>
            ) : (
              <div className="border-2 border-dashed border-gray-100 rounded-2xl p-8 text-center">
                <p className="text-sm text-gray-400">No follow-up planned yet.</p>
              </div>
            )}
          </TooltipWrapper>
        </Section>
      </div>
    </div>
  );
}
