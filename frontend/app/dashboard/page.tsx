"use client";

import { useEffect, useState } from "react";
import ContentSubmissionForm from "@/components/content-submission-form";
import OutputTypeSelector from "@/components/output-type-selector";
import GenerationControls from "@/components/generation-controls";
import OutputPreviewCard from "@/components/output-preview-card";
import { Button } from "@/components/ui/button";
import {
  listOutputTypes,
  generateOutputs,
  generateFromMedia,
  type GenerationParams,
} from "@/lib/api-client";

interface OutputResult {
  status: "done" | "failed";
  data?: Record<string, unknown>;
  error?: string;
}

export default function Dashboard() {
  const [sourceContent, setSourceContent] = useState("");
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  const [availableTypes, setAvailableTypes] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [params, setParams] = useState<GenerationParams>({});
  const [results, setResults] = useState<Record<string, OutputResult | { status: "generating" }>>({});
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listOutputTypes()
      .then(setAvailableTypes)
      .catch(() => setError("Could not reach the backend — is it running on :8000?"));
  }, []);

  async function handleGenerate() {
    const usingMedia = !!mediaFile;
    if ((!usingMedia && !sourceContent.trim()) || selectedTypes.length === 0) return;

    setError(null);
    setGenerating(true);
    setResults(Object.fromEntries(selectedTypes.map((t) => [t, { status: "generating" as const }])));

    try {
      const response = usingMedia
        ? await generateFromMedia(mediaFile!, selectedTypes, params)
        : await generateOutputs({ source_content: sourceContent, output_types: selectedTypes, params });
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  const hasSource = mediaFile !== null || sourceContent.trim().length > 0;
  const canGenerate = hasSource && selectedTypes.length > 0 && !generating;

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Content Transformation Platform</h1>
        <p className="text-sm text-gray-500">
          Submit source content once, generate every deliverable you need from it.
        </p>
      </div>

      <ContentSubmissionForm
        value={sourceContent}
        onChange={setSourceContent}
        mediaFile={mediaFile}
        onMediaFileChange={setMediaFile}
      />

      <OutputTypeSelector
        availableTypes={availableTypes}
        selected={selectedTypes}
        onChange={setSelectedTypes}
      />

      <GenerationControls params={params} onChange={setParams} />

      <div className="flex items-center gap-3">
        <Button onClick={handleGenerate} disabled={!canGenerate}>
          {generating ? "Generating..." : "Generate"}
        </Button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      {Object.keys(results).length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {Object.entries(results).map(([type, result]) => (
            <OutputPreviewCard key={type} outputType={type} result={result} />
          ))}
        </div>
      )}
    </main>
  );
}
