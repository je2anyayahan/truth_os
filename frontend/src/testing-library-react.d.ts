declare module "@testing-library/react" {
  import type { ReactElement } from "react";
  export function render(ui: ReactElement, options?: unknown): unknown;
  export const screen: {
    getByRole: (role: string, options?: { name?: string | RegExp }) => HTMLElement;
    [key: string]: unknown;
  };
}
