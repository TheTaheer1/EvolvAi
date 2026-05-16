import * as React from "react";

import { cn } from "@/lib/utils";

export const Alert = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div role="alert" className={cn("rounded-xl border bg-muted/40 p-4 text-sm", className)} {...props} />;
export const AlertTitle = ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => <h5 className={cn("mb-1 font-medium", className)} {...props} />;
export const AlertDescription = ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => <div className={cn("text-muted-foreground", className)} {...props} />;
