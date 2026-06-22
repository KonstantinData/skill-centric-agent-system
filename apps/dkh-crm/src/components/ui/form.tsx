import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function Field(props: ComponentProps<"input">) {
  return <input {...props} className={cn("field", props.className)} />;
}

export function Textarea(props: ComponentProps<"textarea">) {
  return <textarea {...props} className={cn("textarea", props.className)} />;
}

export function Select(props: ComponentProps<"select">) {
  return <select {...props} className={cn("select", props.className)} />;
}

export function Label({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("label", className)}>
      <span>{label}</span>
      {children}
    </label>
  );
}
