import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type LinkButtonProps = ComponentProps<"a"> & {
  variant?: "primary" | "secondary";
};

export function LinkButton({
  variant = "secondary",
  className,
  ...props
}: LinkButtonProps) {
  return (
    <a
      {...props}
      className={cn(
        "btn",
        variant === "primary" && "btn-primary",
        variant === "secondary" && "btn-secondary",
        className,
      )}
    />
  );
}
