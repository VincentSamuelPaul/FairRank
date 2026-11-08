import { Link, useParams } from 'react-router-dom'
import { Async, EmptyState } from '@/components/states'
import { BandPill } from '@/components/score'
import { useMe } from '@/lib/auth'
import { stageLabel } from '@/lib/format'
import { useMoveStage, usePipeline } from '@/lib/queries'
import type { Stage } from '@/lib/types'

/** The board. Moves are a dropdown (not drag and drop), and only valid human moves are offered. */
export function PipelineBoard({ reqId }: { reqId: string }) {
  const { data: user } = useMe()
  const query = usePipeline(reqId)
  const move = useMoveStage(reqId)
  const canMove = user?.role === 'recruiter'
  return (
    <div className="space-y-4">
      <p className="text-small text-text-2">
        Candidates move on their own when a CV is screened, when you submit, and when the client decides. A score never moves anyone.
      </p>
      {move.isError && <p role="alert" className="text-small text-bad">{move.error.message}</p>}
      <Async query={query} isEmpty={(d) => d.columns.every((c) => c.candidates.length === 0)} empty={<EmptyState title="Nobody in the pipeline yet">Upload CVs to start.</EmptyState>}>
        {(data) => (
          <div className="-mx-(--gutter) overflow-x-auto px-(--gutter) pb-4 [scrollbar-width:thin]" tabIndex={0} role="region" aria-label="Pipeline board, scrolls sideways on small screens">
            <div className="grid snap-x snap-mandatory items-start grid-flow-col auto-cols-[minmax(8.5rem,1fr)] gap-3 max-sm:auto-cols-[78%]">
              {data.columns.map((col) => (
                <section key={col.stage} aria-label={col.label} className="snap-start rounded-card border bg-surface-panel p-2">
                  <h3 className="flex items-center justify-between gap-2 px-1.5 py-1.5 text-small font-medium text-text-1">
                    <span className="flex items-center gap-2">
                      <span aria-hidden className="size-2 rounded-full" style={{ background: `var(--stage-${col.stage})` }} />
                      {col.label}
                    </span>
                    <span className="rounded-pill border px-2 text-small tabular-nums text-text-2">{col.candidates.length}</span>
                  </h3>
                  <ul className="space-y-2">
                    {col.candidates.length === 0 && <li className="px-2 py-6 text-center text-small text-text-3">No one here</li>}
                    {col.candidates.map((c) => (
                      <li key={c.id} className="space-y-2 rounded-input border bg-surface-1 p-3 text-small">
                        <Link to={`/candidates/${c.id}`} className="block font-medium text-text-1 hover:underline">{c.full_name}</Link>
                        <p title={c.current_role} className="truncate text-small text-text-2">{c.current_role || c.external_id}</p>
                        <div className="flex items-center justify-between">
                          {c.band && c.score !== null ? (
                            <span className="flex items-center gap-1.5"><span className="font-semibold tabular-nums">{Math.round(c.score)}</span><BandPill band={c.band} /></span>
                          ) : (
                            <span className="text-small text-text-2">{c.state === 'needs_manual_review' ? 'Manual review' : 'Not scored'}</span>
                          )}
                        </div>
                        {canMove && c.allowed_moves.length > 0 && (
                          <select
                            aria-label={`Move ${c.full_name}`}
                            value=""
                            disabled={move.isPending}
                            onChange={(e) => e.target.value && move.mutate({ id: c.id, stage: e.target.value as Stage })}
                            className="h-9 w-full rounded-input border bg-transparent px-2 text-small text-text-2 hover:border-border-strong focus-visible:outline-2 focus-visible:outline-signal max-md:h-11"
                          >
                            <option value="">Move to…</option>
                            {c.allowed_moves.map((m) => (
                              <option key={m} value={m}>{stageLabel(m)}</option>
                            ))}
                          </select>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </div>
        )}
      </Async>
    </div>
  )
}

export function PipelinePage() {
  const { id = '' } = useParams()
  return <PipelineBoard reqId={id} />
}
