"use client";

import { useRef, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ingestFile, ingestUrl } from "@/lib/api-client";

type InputMode = "text" | "url" | "media";

interface ContentSubmissionFormProps {
  value: string;
  onChange: (value: string) => void;
  // Set when the operator picks an image/video — /generate-from-media is
  // used instead of /generate for this submission. Cleared when they switch
  // back to text/URL/document input.
  mediaFile: File | null;
  onMediaFileChange: (file: File | null) => void;
}

const MODES: { id: InputMode; label: string }[] = [
  { id: "text", label: "Paste Text / Upload Document" },
  { id: "url", label: "From URL" },
  { id: "media", label: "Image / Video" },
];

export default function ContentSubmissionForm({
  value,
  onChange,
  mediaFile,
  onMediaFileChange,
}: ContentSubmissionFormProps) {
  const [mode, setMode] = useState<InputMode>("text");
  const [urlInput, setUrlInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const docInputRef = useRef<HTMLInputElement>(null);
  const mediaInputRef = useRef<HTMLInputElement>(null);

  function switchMode(next: InputMode) {
    setMode(next);
    setError(null);
    if (next !== "media") onMediaFileChange(null);
  }

  async function handleDocSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const text = await ingestFile(file);
      onChange(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
      if (docInputRef.current) docInputRef.current.value = "";
    }
  }

  async function handleUrlFetch() {
    if (!urlInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const text = await ingestUrl(urlInput.trim());
      onChange(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch that URL");
    } finally {
      setLoading(false);
    }
  }

  function handleMediaSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    onMediaFileChange(file);
    onChange(""); // media submissions don't use the text field
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Source Content</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => switchMode(m.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                mode === m.id ? "bg-accent text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {mode === "text" && (
          <div className="space-y-3">
            <Textarea
              rows={8}
              placeholder="Paste your source content here — a report, article, advisory, incident summary, or any free-form text..."
              value={value}
              onChange={(e) => onChange(e.target.value)}
            />
            <div className="flex items-center gap-3">
              <input
                ref={docInputRef}
                type="file"
                accept=".txt,.md,.pdf,.docx"
                className="hidden"
                onChange={handleDocSelect}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => docInputRef.current?.click()}
                disabled={loading}
              >
                {loading ? "Extracting..." : "Upload document (.txt / .md / .pdf / .docx)"}
              </Button>
            </div>
          </div>
        )}

        {mode === "url" && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input
                type="url"
                placeholder="https://example.com/article"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
              />
              <Button type="button" onClick={handleUrlFetch} disabled={loading || !urlInput.trim()}>
                {loading ? "Fetching..." : "Fetch"}
              </Button>
            </div>
            {value && mode === "url" && (
              <Textarea rows={6} value={value} onChange={(e) => onChange(e.target.value)} />
            )}
          </div>
        )}

        {mode === "media" && (
          <div className="space-y-3">
            <input
              ref={mediaInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
              className="hidden"
              onChange={handleMediaSelect}
            />
            <Button type="button" variant="outline" onClick={() => mediaInputRef.current?.click()}>
              {mediaFile ? `Selected: ${mediaFile.name}` : "Select an image or video"}
            </Button>
            <p className="text-xs text-gray-500">
              Gemini reads the image/video directly — no text extraction. Supported: JPG, PNG,
              WEBP, MP4, MOV, WEBM.
            </p>
          </div>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
      </CardContent>
    </Card>
  );
}
