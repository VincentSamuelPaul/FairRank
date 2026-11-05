import { AppShell } from '@/components/AppShell'

/** Stand-in for screens that land later in the plan. */
export function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <AppShell title={title}>
      <p className="mt-2 text-sm text-muted-foreground">{note}</p>
    </AppShell>
  )
}
