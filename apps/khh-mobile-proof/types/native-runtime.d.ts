declare module "react/jsx-runtime" {
  export const Fragment: unknown;
  export function jsx(type: unknown, props: unknown, key?: unknown): unknown;
  export function jsxs(type: unknown, props: unknown, key?: unknown): unknown;
}

declare module "react-native" {
  type NativeComponent = (props: Record<string, unknown>) => unknown;

  export const ScrollView: NativeComponent;
  export const Text: NativeComponent;
  export const View: NativeComponent;
  export const StyleSheet: {
    create<T extends Record<string, unknown>>(styles: T): T;
  };
}
