import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type ButtonProps = ComponentProps<"button"> & {
  variant?: "primary" | "secondary" | "danger";
};

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={cn(
        "btn",
        variant === "primary" && "btn-primary",
        variant === "secondary" && "btn-secondary",
        variant === "danger" && "btn-danger",
        className,
      )}
    />
  );
}

type LinkButtonProps = ComponentProps<"a"> & {
  variant?: "primary" | "secondary" | "danger";
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
        variant === "danger" && "btn-danger",
        className,
      )}
    />
  );
}
