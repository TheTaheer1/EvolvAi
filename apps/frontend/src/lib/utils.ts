import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatStatus(status?: string | null) {
  return (status || "unknown").replaceAll("_", " ");
}

export function safeDate(value?: string | null) {
  if (!value) return "-";
  try {
    return new Intl.DateTimeFormat("en", {
      hour: "2-digit",
      minute: "2-digit",
      month: "short",
      day: "numeric"
    }).format(new Date(value));
  } catch {
    return "-";
  }
}
