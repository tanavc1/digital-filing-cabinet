"use client";

import { useState, useRef, useEffect } from "react";
import { Search, FileText, Loader2, ChevronDown, ChevronUp, ExternalLink, AlertCircle, Sparkles, Lock, FolderOpen, X, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useWorkspace } from "@/components/providers/workspace-provider";
import api from "@/lib/api";

interface Evidence {
  doc_id: string;
  quote: string;
  start_char: number;
  end_char: number;
  confidence: number;
  chunk_id?: string;
}

interface SearchResult {
  answer: string;
  abstained: boolean;
  sources: Evidence[];
  explanation?: string;
}

export default function SearchHome() {
  const { workspace, docs, docsLoaded } = useWorkspace();
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<number | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Load recent searches from localStorage
    const saved = localStorage.getItem("recentSearches");
    if (saved) {
      setRecentSearches(JSON.parse(saved).slice(0, 5));
    }
  }, []);

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setIsSearching(true);
    setResult(null);

    try {
      const res = await api.post("/query", {
        q: q.trim(),
        workspace_id: workspace.id,
      });
      setResult(res.data);

      // Save to recent searches
      const updated = [q, ...recentSearches.filter(s => s !== q)].slice(0, 5);
      setRecentSearches(updated);
      localStorage.setItem("recentSearches", JSON.stringify(updated));
    } catch (err) {
      console.error("Search failed:", err);
      setResult({
        answer: "An error occurred while searching. Please try again.",
        abstained: true,
        sources: [],
      });
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const handleDeleteSearch = (term: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = recentSearches.filter(s => s !== term);
    setRecentSearches(updated);
    localStorage.setItem("recentSearches", JSON.stringify(updated));
  };

  const handleClearSearches = () => {
    setRecentSearches([]);
    localStorage.removeItem("recentSearches");
  };

  const getDocTitle = (docId: string) => {
    const doc = docs?.find(d => d.doc_id === docId);
    return doc?.title || docId;
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Hero Section */}
      <div className="max-w-4xl mx-auto pt-16 px-6">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Document Search
            </h1>
          </div>
          <p className="text-gray-500 text-lg">
            Ask questions across your documents. Every answer backed by evidence.
          </p>
          <div className="flex items-center justify-center gap-2 mt-3 text-sm text-gray-400">
            <Lock className="w-3.5 h-3.5" />
            <span>100% private • Local AI processing • No cloud</span>
          </div>
        </div>

        {/* Search Box */}
        <div className="relative mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your documents..."
              className="w-full pl-12 pr-32 py-4 text-lg border-2 border-gray-200 rounded-2xl focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 outline-none transition-all shadow-sm hover:shadow-md"
              disabled={isSearching}
            />
            <Button
              onClick={() => handleSearch()}
              disabled={isSearching || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white px-6 py-2 rounded-xl"
            >
              {isSearching ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Search
                </>
              )}
            </Button>
          </div>

          {/* Document count indicator - only show after docs loaded */}
          {docsLoaded && (
            <div className="flex items-center justify-center gap-2 mt-3 text-sm text-gray-500">
              <FolderOpen className="w-4 h-4" />
              <span>Searching across {docs.length} document{docs.length !== 1 ? 's' : ''} in {workspace.label}</span>
            </div>
          )}
        </div>

        {/* Recent Searches */}
        {!result && recentSearches.length > 0 && (
          <div className="mb-8 relative group">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-500">Recent searches:</p>
              <button
                onClick={handleClearSearches}
                className="text-xs text-gray-400 hover:text-red-500 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 className="w-3 h-3" /> Clear all
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {recentSearches.map((s, i) => (
                <div
                  key={i}
                  className="group/item relative inline-flex"
                >
                  <button
                    onClick={() => {
                      setQuery(s);
                      handleSearch(s);
                    }}
                    className="pl-3 pr-8 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-sm text-gray-600 transition-colors"
                  >
                    {s}
                  </button>
                  <button
                    onClick={(e) => handleDeleteSearch(s, e)}
                    className="absolute right-1 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center rounded-full text-gray-400 hover:text-red-500 hover:bg-gray-300/50 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6 pb-16">
            {/* Answer Card */}
            <Card className={`border-2 ${result.abstained ? 'border-amber-200 bg-amber-50/50' : 'border-green-200 bg-green-50/50'}`}>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  {result.abstained ? (
                    <AlertCircle className="w-5 h-5 text-amber-500" />
                  ) : (
                    <Sparkles className="w-5 h-5 text-green-500" />
                  )}
                  <CardTitle className="text-lg">
                    {result.abstained ? "Insufficient Evidence" : "Answer"}
                  </CardTitle>
                  {!result.abstained && (
                    <Badge variant="secondary" className="ml-auto bg-green-100 text-green-700">
                      {result.sources.length} source{result.sources.length !== 1 ? 's' : ''}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                  {result.answer}
                </p>
              </CardContent>
            </Card>

            {/* Evidence Cards */}
            {result.sources.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Evidence Citations
                </h3>
                <div className="space-y-3">
                  {result.sources.map((source, index) => (
                    <Card
                      key={index}
                      className="border border-gray-200 hover:border-indigo-300 transition-colors cursor-pointer"
                      onClick={() => setExpandedEvidence(expandedEvidence === index ? null : index)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <FileText className="w-4 h-4 text-indigo-500" />
                              <span className="font-medium text-gray-900">
                                {getDocTitle(source.doc_id)}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                {Math.round(source.confidence * 100)}% match
                              </Badge>
                            </div>
                            <p className={`text-gray-600 text-sm ${expandedEvidence === index ? '' : 'line-clamp-2'}`}>
                              "{source.quote}"
                            </p>
                          </div>
                          <Button variant="ghost" size="sm" className="shrink-0">
                            {expandedEvidence === index ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                          </Button>
                        </div>
                        {expandedEvidence === index && (
                          <div className="mt-3 pt-3 border-t flex items-center gap-2">
                            <Button variant="outline" size="sm" asChild>
                              <a href={`/viewer/${source.doc_id}?workspace_id=${workspace.id}&quote=${encodeURIComponent(source.quote)}`}>
                                <ExternalLink className="w-3 h-3 mr-1" />
                                View in Document
                              </a>
                            </Button>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Try Another Search */}
            <div className="text-center pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setResult(null);
                  setQuery("");
                  inputRef.current?.focus();
                }}
              >
                Ask Another Question
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
