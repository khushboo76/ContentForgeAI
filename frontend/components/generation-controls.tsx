"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import {
  TONE_OPTIONS,
  SENTIMENT_OPTIONS,
  AUDIENCE_OPTIONS,
  DETAIL_LEVEL_OPTIONS,
  LANGUAGE_OPTIONS,
} from "@/lib/constants";
import type { GenerationParams } from "@/lib/api-client";

interface GenerationControlsProps {
  params: GenerationParams;
  onChange: (params: GenerationParams) => void;
}

function ControlField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string | undefined;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-gray-500">{label}</label>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </Select>
    </div>
  );
}

export default function GenerationControls({ params, onChange }: GenerationControlsProps) {
  const update = (key: keyof GenerationParams) => (value: string) =>
    onChange({ ...params, [key]: value });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generation Controls</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <ControlField label="Tone" value={params.tone} options={TONE_OPTIONS} onChange={update("tone")} />
          <ControlField
            label="Sentiment"
            value={params.sentiment}
            options={SENTIMENT_OPTIONS}
            onChange={update("sentiment")}
          />
          <ControlField
            label="Audience"
            value={params.audience}
            options={AUDIENCE_OPTIONS}
            onChange={update("audience")}
          />
          <ControlField
            label="Language"
            value={params.language}
            options={LANGUAGE_OPTIONS}
            onChange={update("language")}
          />
          <ControlField
            label="Detail Level"
            value={params.detail_level}
            options={DETAIL_LEVEL_OPTIONS}
            onChange={update("detail_level")}
          />
        </div>
      </CardContent>
    </Card>
  );
}
