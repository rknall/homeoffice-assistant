import { create } from 'zustand'

export interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbState {
  items: BreadcrumbItem[]
  setItems: (items: BreadcrumbItem[]) => void
  clear: () => void
}

export const useBreadcrumb = create<BreadcrumbState>((set) => ({
  items: [],
  setItems: (items: BreadcrumbItem[]) => set({ items }),
  clear: () => set({ items: [] }),
}))
