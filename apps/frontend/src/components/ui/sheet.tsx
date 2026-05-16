import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as React from "react";

import { cn } from "@/lib/utils";

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;
export const SheetPortal = DialogPrimitive.Portal;
export const SheetOverlay = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Overlay>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>>(({ className, ...props }, ref) => <DialogPrimitive.Overlay ref={ref} className={cn("fixed inset-0 z-50 bg-black/70", className)} {...props} />);
SheetOverlay.displayName = DialogPrimitive.Overlay.displayName;
export const SheetContent = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Content>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>>(({ className, ...props }, ref) => <SheetPortal><SheetOverlay /><DialogPrimitive.Content ref={ref} className={cn("fixed right-0 top-0 z-50 h-full w-80 border-l bg-card p-6 shadow-glow", className)} {...props} /></SheetPortal>);
SheetContent.displayName = DialogPrimitive.Content.displayName;
