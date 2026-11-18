"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StatusIndicator from "@/components/status-indicator";
import { OUTPUT_TYPE_LABELS } from "@/lib/constants";
import { Send, Edit3, Check, Download } from "lucide-react";

interface OutputResult {
  status: "done" | "failed";
  data?: Record<string, unknown>;
  error?: string;
}

interface OutputPreviewCardProps {
  outputType: string;
  result: OutputResult | { status: "generating" };
  onPublishClick?: (outputType: string, data: Record<string, unknown>) => void;
}

export default function OutputPreviewCard({
  outputType,
  result,
  onPublishClick,
}: OutputPreviewCardProps) {
  const status = result.status === "generating" ? "generating" : result.status;
  const initialData = result.status === "done" && result.data ? result.data : null;

  const [editableData, setEditableData] = useState<Record<string, unknown> | null>(initialData);
  const [isEditing, setIsEditing] = useState(false);

  // A card is first mounted in its "generating" state. Keep its editor state
  // in sync when the request returns, rather than setting state during render.
  useEffect(() => {
    setEditableData(initialData);
    setIsEditing(false);
  }, [initialData]);

  const currentData = editableData || initialData || {};
  const generationNotice =
    typeof currentData._generation_notice === "string" ? currentData._generation_notice : null;

  function handleExport() {
    if (!currentData || Object.keys(currentData).length === 0) return;
    const blob = new Blob([JSON.stringify(currentData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${outputType}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function renderViewer(type: string, data: Record<string, unknown>) {
    switch (type) {
      case "linkedin_post":
        return (
          <div className="space-y-2">
            <p className="whitespace-pre-wrap font-medium text-gray-900">{String(data.hook || "")}</p>
            <p className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">{String(data.body || "")}</p>
            <p className="text-accent text-sm font-medium">
              {Array.isArray(data.hashtags) ? (data.hashtags as string[]).join(" ") : ""}
            </p>
            {!!data.cta && (
              <p className="text-xs bg-gray-50 border rounded p-2 text-gray-600 font-medium">
                {String(data.cta)}
              </p>
            )}
          </div>
        );
      case "advisory":
        return (
          <div className="space-y-2 text-sm">
            <p>
              <span className="font-semibold text-gray-700">Severity: </span>
              <span className="uppercase font-bold text-accent">{String(data.severity || "")}</span>
            </p>
            <p>
              <span className="font-semibold text-gray-700">Situation: </span>
              {String(data.situation || "")}
            </p>
            <p>
              <span className="font-semibold text-gray-700">Impact: </span>
              {String(data.impact || "")}
            </p>
            <div>
              <span className="font-semibold text-gray-700">Recommended Actions:</span>
              <ul className="list-disc pl-5 mt-1 space-y-1">
                {(data.recommended_actions as string[])?.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          </div>
        );
      case "executive_summary":
        return (
          <div className="space-y-3 text-sm">
            <p className="text-gray-800 leading-relaxed">{String(data.summary || "")}</p>
            <div>
              <p className="font-semibold text-gray-900 mb-1">Key Findings</p>
              <ul className="list-disc pl-5 space-y-1">
                {(data.key_findings as string[])?.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
            {!!(data.recommendations as string[])?.length && (
              <div>
                <p className="font-semibold text-gray-900 mb-1">Recommendations</p>
                <ul className="list-disc pl-5 space-y-1">
                  {(data.recommendations as string[]).map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      case "presentation":
        return (
          <div className="space-y-3">
            {(data.slides as Array<{ title: string; bullets: string[]; speaker_notes: string }>)?.map(
              (slide, i) => (
                <div key={i} className="rounded-lg border border-gray-100 bg-gray-50/50 p-3 text-sm">
                  <p className="font-semibold text-gray-900">
                    Slide {i + 1}: {slide.title}
                  </p>
                  <ul className="list-disc pl-5 my-1.5 space-y-0.5 text-gray-700">
                    {slide.bullets?.map((b, j) => (
                      <li key={j}>{b}</li>
                    ))}
                  </ul>
                  <p className="mt-1 text-xs text-gray-500 italic">Speaker notes: {slide.speaker_notes}</p>
                </div>
              )
            )}
          </div>
        );
      case "infographic":
        return (
          <div className="space-y-2.5 text-sm">
            {!!data.image_base64 && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`data:image/png;base64,${data.image_base64}`}
                alt="Generated infographic"
                className="w-full rounded-lg border border-gray-100 shadow-sm"
              />
            )}
            <div>
              <p className="font-semibold text-gray-900 mb-1">Key Messages</p>
              <ul className="list-disc pl-5 space-y-0.5">
                {(data.key_messages as string[])?.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="font-semibold text-gray-900 mb-1">Sections</p>
              <ol className="list-decimal pl-5 space-y-0.5">
                {(data.sections as string[])?.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
            <p className="text-xs text-gray-500">{String(data.layout_recommendations || "")}</p>
          </div>
        );
      case "email":
        return (
          <div className="space-y-3 text-sm">
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Subject</span>
              <p className="mt-0.5 font-medium text-gray-900">{String(data.subject || "")}</p>
            </div>
            <div className="whitespace-pre-wrap text-gray-700 leading-relaxed border rounded-lg p-3 bg-white text-sm">
              {String(data.body || "")}
            </div>
            {!!(data.key_points as string[])?.length && (
              <div>
                <p className="font-semibold text-gray-900 mb-1">Key Points</p>
                <ul className="list-disc pl-5 space-y-0.5 text-gray-700">
                  {(data.key_points as string[]).map((pt, i) => (
                    <li key={i}>{pt}</li>
                  ))}
                </ul>
              </div>
            )}
            {!!data.call_to_action && (
              <p className="rounded-lg border border-accent/30 bg-accent/5 px-3 py-2 text-xs font-medium text-accent">
                CTA: {String(data.call_to_action)}
              </p>
            )}
          </div>
        );
      default:
        return <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(data, null, 2)}</pre>;
    }
  }

  function renderEditor(type: string, data: Record<string, unknown>) {
    if (type === "linkedin_post") {
      return (
        <div className="space-y-2">
          <label className="text-xs font-semibold text-gray-600">Hook</label>
          <input
            type="text"
            className="w-full rounded border border-gray-300 p-2 text-sm"
            value={String(data.hook || "")}
            onChange={(e) => setEditableData({ ...data, hook: e.target.value })}
          />
          <label className="text-xs font-semibold text-gray-600">Body</label>
          <textarea
            rows={5}
            className="w-full rounded border border-gray-300 p-2 text-sm"
            value={String(data.body || "")}
            onChange={(e) => setEditableData({ ...data, body: e.target.value })}
          />
          <label className="text-xs font-semibold text-gray-600">Hashtags (space-separated)</label>
          <input
            type="text"
            className="w-full rounded border border-gray-300 p-2 text-sm"
            value={Array.isArray(data.hashtags) ? (data.hashtags as string[]).join(" ") : ""}
            onChange={(e) =>
              setEditableData({
                ...data,
                hashtags: e.target.value.split(" ").filter(Boolean),
              })
            }
          />
        </div>
      );
    } else {
      // General JSON editor for other types
      return (
        <div className="space-y-1">
          <label className="text-xs font-semibold text-gray-600">Raw Deliverable JSON</label>
          <textarea
            rows={8}
            className="w-full font-mono text-xs rounded border border-gray-300 p-2"
            value={JSON.stringify(data, null, 2)}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                setEditableData(parsed);
              } catch {
                // Keep typing
              }
            }}
          />
        </div>
      );
    }
  }

  return (
    <Card className="flex flex-col justify-between">
      <div>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-base">{OUTPUT_TYPE_LABELS[outputType] ?? outputType}</CardTitle>
          <div className="flex items-center gap-2">
            {result.status === "done" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditing(!isEditing)}
                className="h-7 text-xs px-2 gap-1 text-gray-600"
              >
                {isEditing ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-600" /> Done
                  </>
                ) : (
                  <>
                    <Edit3 className="h-3 w-3" /> Edit
                  </>
                )}
              </Button>
            )}
            <StatusIndicator status={status} />
          </div>
        </CardHeader>
        <CardContent>
          {result.status === "generating" && <p className="text-sm text-gray-400">Generating...</p>}
          {result.status === "failed" && <p className="text-sm text-red-600">{result.error}</p>}
          {result.status === "done" && (
            <div>
              {generationNotice && (
                <p className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs leading-relaxed text-amber-900">
                  {generationNotice}
                </p>
              )}
              {isEditing ? renderEditor(outputType, currentData) : renderViewer(outputType, currentData)}
            </div>
          )}
        </CardContent>
      </div>

      {result.status === "done" && (
        <div className="flex items-center justify-between border-t border-gray-100 bg-gray-50/50 p-3 rounded-b-xl gap-2 mt-4">
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={handleExport}>
            <Download className="h-3.5 w-3.5" /> Export JSON
          </Button>

          {onPublishClick && (
            <Button
              size="sm"
              className="gap-1.5 text-xs font-medium"
              onClick={() => onPublishClick(outputType, currentData)}
            >
              <Send className="h-3.5 w-3.5" /> Publish / Distribute
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}
