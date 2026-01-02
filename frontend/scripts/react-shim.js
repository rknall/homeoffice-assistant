// React shim for plugin builds
// This provides React from the global scope (window.React) for dynamically loaded plugins
// The host app must expose React globally before plugins are loaded

const React = window.React

// Re-export all React exports
export const {
  Children,
  Component,
  Fragment,
  Profiler,
  PureComponent,
  StrictMode,
  Suspense,
  cloneElement,
  createContext,
  createElement,
  createFactory,
  createRef,
  forwardRef,
  isValidElement,
  lazy,
  memo,
  startTransition,
  unstable_act,
  useCallback,
  useContext,
  useDebugValue,
  useDeferredValue,
  useEffect,
  useId,
  useImperativeHandle,
  useInsertionEffect,
  useLayoutEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  useSyncExternalStore,
  useTransition,
  version,
} = React

// JSX runtime exports (for automatic JSX transform)
export const jsx = (type, props, key) => {
  if (key !== undefined) {
    props = { ...props, key }
  }
  return React.createElement(type, props)
}

export const jsxs = jsx
export const jsxDEV = jsx

export default React
