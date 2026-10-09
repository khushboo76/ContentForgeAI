import { InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      type="checkbox"
      className={cn(
        "h-4 w-4 rounded border-gray-300 text-accent focus:ring-accent/40",
        className
      )}
      {...props}
    />
  )
);
Checkbox.displayName = "Checkbox";
