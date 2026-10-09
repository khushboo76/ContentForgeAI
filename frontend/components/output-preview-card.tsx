"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StatusIndicator from "@/components/status-indicator";
import { OUTPUT_TYPE_LABELS } from "@/lib/constants";

interface OutputResult {
  status: "done" | "failed";
  data?: Record<string, unknown>;
  error?: string;
}

interface OutputPreviewCardProps {
  outputType: string;
  result: OutputResult | { status: "generating" };
}

function renderBody(outputType: string, data: Record<string, unknown>) {
  switch (outputType) {
    case "linkedin_post":
      return (
        <div className="space-y-2">
          <p className="whitespace-pre-wrap">{String(data.hook)}</p>
          <p className="whitespace-pre-wrap">{String(data.body)}</p>
          <p className="text-accent">{(data.hashtags as string[])?.join(" ")}</p>
          {!!data.cta && <p className="font-medium">{String(data.cta)}</p>}
        </div>
      );
    case "twitter_post":
      return (
        <div className="space-y-2">
          {(data.posts as string[])?.map((post, i) => (
            <p key={i} className="rounded-lg border border-gray-100 p-2">
              {post}
            </p>
          ))}
        </div>
      );
    case "advisory":
      return (
        <div className="space-y-2">
          <p>
            <span className="font-medium">Severity: </span>
            {String(data.severity)}
          </p>
          <p>
            <span className="font-medium">Situation: </span>
            {String(data.situation)}
          </p>
          <p>
            <span className="font-medium">Impact: </span>
            {String(data.impact)}
          </p>
          <ul className="list-disc pl-5">
            {(data.recommended_actions as string[])?.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      );
    case "executive_summary":
      return (
        <div className="space-y-2">
          <p>{String(data.summary)}</p>
          <ul className="list-disc pl-5">
            {(data.key_findings as string[])?.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
          {!!(data.recommendations as string[])?.length && (
            <>
              <p className="font-medium">Recommendations</p>
              <ul className="list-disc pl-5">
                {(data.recommendations as string[]).map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      );
    case "presentation":
      return (
        <div className="space-y-3">
          {(data.slides as Array<{ title: string; bullets: string[]; speaker_notes: string }>)?.map(
            (slide, i) => (
              <div key={i} className="rounded-lg border border-gray-100 p-3">
                <p className="font-medium">
                  Slide {i + 1}: {slide.title}
                </p>
                <ul className="list-disc pl-5">
                  {slide.bullets.map((b, j) => (
                    <li key={j}>{b}</li>
                  ))}
                </ul>
                <p className="mt-1 text-xs text-gray-500">{slide.speaker_notes}</p>
              </div>
            )
          )}
        </div>
      );
    case "infographic":
      return (
        <div className="space-y-2">
          {!!data.image_base64 && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`data:image/png;base64,${data.image_base64}`}
              alt="Generated infographic"
              className="w-full rounded-lg border border-gray-100"
            />
          )}
          <ul className="list-disc pl-5">
            {(data.key_messages as string[])?.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
          <p className="font-medium">Sections</p>
          <ol className="list-decimal pl-5">
            {(data.sections as string[])?.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
          <p className="text-xs text-gray-500">{String(data.layout_recommendations)}</p>
        </div>
      );
    case "video_package":
      return (
        <div className="space-y-3">
          <p className="whitespace-pre-wrap">{String(data.script)}</p>
          {(data.storyboard as Array<{ scene_number: number; description: string; narration: string; subtitle: string }>)?.map(
            (scene) => (
              <div key={scene.scene_number} className="rounded-lg border border-gray-100 p-3">
                <p className="font-medium">Scene {scene.scene_number}</p>
                <p className="text-xs text-gray-500">{scene.description}</p>
                <p>{scene.narration}</p>
              </div>
            )
          )}
          <p className="text-xs text-gray-500">{String(data.visual_recommendations)}</p>
        </div>
      );
    default:
      return <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(data, null, 2)}</pre>;
  }
}

export default function OutputPreviewCard({ outputType, result }: OutputPreviewCardProps) {
  const status = result.status === "generating" ? "generating" : result.status;

  function handleExport() {
    if (result.status !== "done") return;
    const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${outputType}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{OUTPUT_TYPE_LABELS[outputType] ?? outputType}</CardTitle>
        <StatusIndicator status={status} />
      </CardHeader>
      <CardContent>
        {result.status === "generating" && <p className="text-gray-400">Generating...</p>}
        {result.status === "failed" && <p className="text-red-600">{result.error}</p>}
        {result.status === "done" && result.data && (
          <>
            {renderBody(outputType, result.data)}
            <Button variant="outline" className="mt-3" onClick={handleExport}>
              Export JSON
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
