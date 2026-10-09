"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { OUTPUT_TYPE_LABELS } from "@/lib/constants";

interface OutputTypeSelectorProps {
  availableTypes: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function OutputTypeSelector({ availableTypes, selected, onChange }: OutputTypeSelectorProps) {
  function toggle(type: string) {
    if (selected.includes(type)) {
      onChange(selected.filter((t) => t !== type));
    } else {
      onChange([...selected, type]);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Output Types</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {availableTypes.map((type) => (
            <label
              key={type}
              className="flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 p-3 text-sm hover:bg-gray-50"
            >
              <Checkbox checked={selected.includes(type)} onChange={() => toggle(type)} />
              {OUTPUT_TYPE_LABELS[type] ?? type}
            </label>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
