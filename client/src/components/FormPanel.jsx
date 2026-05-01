import React, { useState, useEffect, useRef } from "react";
import { useSelector, useDispatch } from "react-redux";
import { updateDraft, setIsSaved } from "../store/InteractionSlice";
import { searchHCPs, submitForm } from "../api/client";

export default function FormPanel() {
  const { draft, isSaved } = useSelector((state) => state.interaction);
  const dispatch = useDispatch();

  const handleUpdate = (field, value) => {
    dispatch(updateDraft({ [field]: value }));
  };

  // HCP Search State
  const [searchQuery, setSearchQuery] = useState(draft.hcp_name || "");
  const [searchResults, setSearchResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    setSearchQuery(draft.hcp_name || "");
  }, [draft.hcp_name]);

  useEffect(() => {
    if (!showDropdown || !searchQuery || searchQuery.length < 2) return;
    const timeoutId = setTimeout(() => {
      searchHCPs(searchQuery)
        .then(res => setSearchResults(res.data))
        .catch(console.error);
    }, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery, showDropdown]);

  // Attendees Local State
  const [attendeesText, setAttendeesText] = useState((draft.attendees || []).join(", "));
  const attendeesRef = useRef(draft.attendees);

  useEffect(() => {
    if (draft.attendees !== attendeesRef.current) {
      attendeesRef.current = draft.attendees;
      const currentArray = attendeesText.split(",").map(s => s.trim()).filter(Boolean);
      if (JSON.stringify(currentArray) !== JSON.stringify(draft.attendees)) {
        setAttendeesText((draft.attendees || []).join(", "));
      }
    }
  }, [draft.attendees, attendeesText]);

  // Materials & Samples State
  const [materialText, setMaterialText] = useState("");
  const [showMaterialInput, setShowMaterialInput] = useState(false);

  const [sampleText, setSampleText] = useState("");
  const [showSampleInput, setShowSampleInput] = useState(false);

  // Saving State
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await submitForm(draft);
      dispatch(setIsSaved(true));
    } catch (err) {
      console.error(err);
      alert("Error saving: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-6 font-inter h-full flex flex-col bg-white rounded-xl shadow-sm">
      <h2 className="text-xl font-bold text-slate-900 mb-6 shrink-0">Interaction Details</h2>
      
      <div className="flex-1">
        {/* SECTION 1 — Top row */}
        <div className="grid grid-cols-2 gap-6 mb-5">
          <div className="relative">
            <label className="block text-sm font-medium text-slate-700 mb-1">HCP Name</label>
            <input 
              type="text" 
              placeholder="Search or select HCP..."
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowDropdown(true);
                if (!e.target.value) {
                  handleUpdate("hcp_id", null);
                  handleUpdate("hcp_name", null);
                }
              }}
              onFocus={() => setShowDropdown(true)}
              onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
            />
            {showDropdown && searchResults.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {searchResults.map(hcp => (
                  <div 
                    key={hcp.id}
                    className="px-4 py-2 hover:bg-slate-50 cursor-pointer border-b last:border-b-0 border-slate-100"
                    onClick={() => {
                      handleUpdate("hcp_id", hcp.id);
                      handleUpdate("hcp_name", hcp.name);
                      setSearchQuery(hcp.name);
                      setShowDropdown(false);
                    }}
                  >
                    <div className="font-medium text-sm text-slate-900">{hcp.name}</div>
                    <div className="text-xs text-slate-500">{hcp.specialty} • {hcp.hospital}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Interaction Type</label>
            <select 
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
              value={draft.interaction_type || "Meeting"}
              onChange={(e) => handleUpdate("interaction_type", e.target.value)}
            >
              <option value="Meeting">Meeting</option>
              <option value="Visit">Visit</option>
              <option value="Call">Call</option>
              <option value="Email">Email</option>
              <option value="Conference">Conference</option>
            </select>
          </div>
        </div>

        {/* SECTION 2 — Second row */}
        <div className="grid grid-cols-2 gap-6 mb-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Date</label>
            <input 
              type="date"
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              value={draft.date || new Date().toISOString().split('T')[0]}
              onChange={(e) => handleUpdate("date", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Time</label>
            <input 
              type="time"
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              value={draft.time || new Date().toLocaleTimeString('en-US', { hour12: false, hour: "2-digit", minute: "2-digit" })}
              onChange={(e) => handleUpdate("time", e.target.value)}
            />
          </div>
        </div>

        {/* SECTION 3 — Attendees */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-700 mb-1">Attendees</label>
          <input 
            type="text"
            placeholder="Enter names or search..."
            className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            value={attendeesText}
            onChange={(e) => {
              setAttendeesText(e.target.value);
              handleUpdate("attendees", e.target.value.split(",").map(s => s.trim()).filter(Boolean));
            }}
          />
        </div>

        {/* SECTION 4 — Topics Discussed */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-700 mb-1">Topics Discussed</label>
          <textarea 
            rows={4}
            placeholder="Enter key discussion points..."
            className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
            value={draft.topics_discussed || ""}
            onChange={(e) => handleUpdate("topics_discussed", e.target.value)}
          ></textarea>
          
          <button 
            className="mt-2 flex items-center space-x-2 px-3 py-1.5 border border-slate-300 rounded-md text-sm text-slate-700 hover:bg-slate-50 transition-colors"
            onClick={(e) => { e.preventDefault(); alert("Voice note feature coming soon"); }}
          >
            <span>🎙</span>
            <span>Summarize from Voice Note (Requires Consent)</span>
          </button>
        </div>

        {/* SECTION 5 — Materials Shared / Samples Distributed */}
        <div className="mb-5">
          <h4 className="text-base font-medium text-slate-900 mb-4">Materials Shared / Samples Distributed</h4>
          
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-slate-700">Materials Shared</label>
              <button 
                onClick={(e) => { e.preventDefault(); setShowMaterialInput(true); }}
                className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-50 text-slate-700"
              >
                🔍 Search/Add
              </button>
            </div>
            
            {showMaterialInput && (
              <input 
                type="text"
                autoFocus
                className="mb-2 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Type material and press Enter..."
                value={materialText}
                onChange={(e) => setMaterialText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && materialText.trim()) {
                    e.preventDefault();
                    const newArr = [...(draft.materials_shared || []), materialText.trim()];
                    handleUpdate("materials_shared", newArr);
                    setMaterialText("");
                    setShowMaterialInput(false);
                  } else if (e.key === "Escape") {
                    setShowMaterialInput(false);
                  }
                }}
                onBlur={() => setShowMaterialInput(false)}
              />
            )}

            {!(draft.materials_shared?.length > 0) ? (
              <p className="text-sm text-slate-400 italic">No materials added</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {draft.materials_shared.map((m, i) => (
                  <span key={i} className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                    {m}
                    <button 
                      onClick={(e) => {
                        e.preventDefault();
                        handleUpdate("materials_shared", draft.materials_shared.filter((_, idx) => idx !== i));
                      }}
                      className="ml-1.5 text-indigo-500 hover:text-indigo-700"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-slate-700">Samples Distributed</label>
              <button 
                onClick={(e) => { e.preventDefault(); setShowSampleInput(true); }}
                className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-50 text-slate-700"
              >
                Add Sample
              </button>
            </div>
            
            {showSampleInput && (
              <input 
                type="text"
                autoFocus
                className="mb-2 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Type sample and press Enter..."
                value={sampleText}
                onChange={(e) => setSampleText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && sampleText.trim()) {
                    e.preventDefault();
                    const newArr = [...(draft.samples_distributed || []), sampleText.trim()];
                    handleUpdate("samples_distributed", newArr);
                    setSampleText("");
                    setShowSampleInput(false);
                  } else if (e.key === "Escape") {
                    setShowSampleInput(false);
                  }
                }}
                onBlur={() => setShowSampleInput(false)}
              />
            )}

            {!(draft.samples_distributed?.length > 0) ? (
              <p className="text-sm text-slate-400 italic">No samples added</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {draft.samples_distributed.map((s, i) => (
                  <span key={i} className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-teal-100 text-teal-800">
                    {s}
                    <button 
                      onClick={(e) => {
                        e.preventDefault();
                        handleUpdate("samples_distributed", draft.samples_distributed.filter((_, idx) => idx !== i));
                      }}
                      className="ml-1.5 text-teal-500 hover:text-teal-700"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* SECTION 6 — Sentiment */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-700 mb-2">Observed/Inferred HCP Sentiment</label>
          <div className="flex items-center gap-6">
            {[
              { label: "Positive", value: "positive", colorClass: "bg-green-500" },
              { label: "Neutral", value: "neutral", colorClass: "bg-slate-500" },
              { label: "Negative", value: "negative", colorClass: "bg-red-500" },
            ].map(opt => {
              const isSelected = (draft.sentiment || "neutral").toLowerCase() === opt.value;
              return (
                <label key={opt.value} className="flex items-center space-x-2 cursor-pointer group">
                  <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${isSelected ? 'border-slate-400' : 'border-slate-300 group-hover:border-slate-400'}`}>
                    {isSelected && <div className={`w-2 h-2 rounded-full ${opt.colorClass}`}></div>}
                  </div>
                  <span className="text-sm text-slate-700">{opt.label}</span>
                  <input 
                    type="radio" 
                    name="sentiment" 
                    value={opt.value} 
                    checked={isSelected}
                    onChange={(e) => handleUpdate("sentiment", e.target.value)}
                    className="hidden"
                  />
                </label>
              );
            })}
          </div>
        </div>

        {/* SECTION 7 — Outcomes */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-700 mb-1">Outcomes</label>
          <textarea 
            rows={3}
            placeholder="Key outcomes or agreements..."
            className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
            value={draft.outcomes || ""}
            onChange={(e) => handleUpdate("outcomes", e.target.value)}
          ></textarea>
        </div>

        {/* SECTION 8 — Follow up Actions */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-700 mb-1">Follow up Actions</label>
          <textarea 
            rows={3}
            placeholder="Enter next steps or tasks..."
            className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
            value={draft.follow_up_actions || ""}
            onChange={(e) => handleUpdate("follow_up_actions", e.target.value)}
          ></textarea>
        </div>

        {/* SECTION 9 — AI Suggested Follow-ups */}
        {draft.ai_suggested_follow_ups?.length > 0 && (
          <div className="mb-5">
            <label className="block text-xs font-medium text-slate-500 mb-2 flex items-center">
              <span className="mr-1">✨</span> AI Suggested Follow-ups:
            </label>
            <div className="space-y-2">
              {draft.ai_suggested_follow_ups.map((suggestion, idx) => (
                <div key={idx} className="flex items-start justify-between bg-indigo-50 rounded px-3 py-2 border border-indigo-100">
                  <div className="flex-1 mr-2 flex items-start">
                    <span className="mr-2 text-indigo-400">•</span>
                    <span className="text-sm text-slate-600">{suggestion}</span>
                  </div>
                  <button 
                    onClick={(e) => {
                      e.preventDefault();
                      const currentActions = draft.follow_up_actions ? draft.follow_up_actions.trim() : "";
                      const newActions = currentActions ? currentActions + "\n" + suggestion : suggestion;
                      handleUpdate("follow_up_actions", newActions);
                    }}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-white border border-indigo-200 rounded px-2 py-1 shrink-0 mt-0.5"
                  >
                    + Add
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* BOTTOM — Save button */}
      <div className="mt-8 shrink-0">
        {isSaved ? (
          <div className="w-full py-3 rounded-lg border border-green-200 bg-green-50 text-green-700 text-center font-medium flex items-center justify-center">
            <span className="mr-2">✓</span> Saved
          </div>
        ) : (
          <button 
            onClick={handleSave}
            disabled={isSaving}
            className={`w-full py-3 rounded-lg font-medium text-white text-center transition-colors ${isSaving ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'}`}
          >
            {isSaving ? "Saving..." : "Save Interaction"}
          </button>
        )}
      </div>
    </div>
  );
}
