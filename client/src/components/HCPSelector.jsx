import { useEffect, useState, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { setHCPs, setSearchResults, setSelectedHCP } from "../store/HCPSlice";
import { updateDraft } from "../store/InteractionSlice";
import { getHCPs, searchHCPs } from "../api/client";

export default function HCPSelector() {
  const dispatch = useDispatch();

  const { searchResults, selectedHCP } = useSelector(
    (state) => state.hcp
  );

  const [query, setQuery] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);

  // Fetch all HCPs on mount
  useEffect(() => {
    const fetchHCPs = async () => {
      try {
        const data = await getHCPs();
        dispatch(setHCPs(data.data));
      } catch (err) {
        console.error("Failed to fetch HCPs", err);
      }
    };
    fetchHCPs();
  }, [dispatch]);

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(async () => {
      if (!query.trim()) return;
      try {
        const results = await searchHCPs(query);
        dispatch(setSearchResults(results.data));
        setShowDropdown(true);
      } catch (err) {
        console.error("Search failed", err);
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [query, dispatch]);

  const handleSelect = (hcp) => {
    dispatch(setSelectedHCP(hcp));
    dispatch(
      updateDraft({
        hcp_id: hcp.id,
        hcp_name: hcp.name,
      })
    );
    setShowDropdown(false);
  };

  const handleReset = () => {
    dispatch(setSelectedHCP(null));
    setQuery("");
  };

  const tierStyles = {
    tier1: "bg-indigo-100 text-indigo-700",
    tier2: "bg-blue-100 text-blue-700",
    tier3: "bg-gray-100 text-gray-600",
  };

  return (
    <div className="w-full font-inter">
      {/* Selected HCP Card */}
      {selectedHCP ? (
        <div className="bg-white shadow-sm rounded-xl p-4 mb-4 border">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold text-lg text-gray-900">
                {selectedHCP.name}
              </h3>
              <p className="text-sm text-gray-500">
                {selectedHCP.specialty} · {selectedHCP.hospital}
              </p>
            </div>

            <span
              className={`px-2 py-1 text-xs rounded-full ${
                tierStyles[selectedHCP.tier]
              }`}
            >
              {selectedHCP.tier}
            </span>
          </div>

          <button
            onClick={handleReset}
            className="mt-2 text-sm text-blue-600 hover:underline"
          >
            Change HCP
          </button>
        </div>
      ) : (
        <div className="relative">
          {/* Search Input */}
          <input
            type="text"
            placeholder="Search HCP by name or hospital..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full px-4 py-2 border rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />

          {/* Dropdown */}
          {showDropdown && searchResults?.length > 0 && (
            <div className="absolute z-10 w-full bg-white border mt-2 rounded-xl shadow-md max-h-64 overflow-y-auto">
              {searchResults.map((hcp) => (
                <div
                  key={hcp.id}
                  onClick={() => handleSelect(hcp)}
                  className="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b last:border-none"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-gray-900">
                        {hcp.name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {hcp.specialty} · {hcp.hospital}
                      </p>
                    </div>

                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        tierStyles[hcp.tier]
                      }`}
                    >
                      {hcp.tier}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}