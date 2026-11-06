import type { DetailedHTMLProps, HTMLAttributes } from "react";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "math-field": DetailedHTMLProps<
        HTMLAttributes<HTMLElement> & {
          value?: string;
          "read-only"?: boolean;
          "virtual-keyboard-mode"?: string;
          placeholder?: string;
        },
        HTMLElement
      >;
    }
  }
}

export {};
