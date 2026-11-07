import { Link, useParams } from 'react-router-dom'
import { Async, EmptyState } from '@/components/states'
import { BandPill } from '@/components/score'
import { Select } from '@/components/ui/field'
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
      <p className="text-small text-muted-foreground">
        Candidates move on their own when a CV is screened, when you submit, and when the client decides. A score never moves anyone.
      </p>
      {move.isError && <p role="alert" className="text-small text-destructive">{move.error.message}</p>}
      <Async query={query} isEmpty={(d) => d.columns.every((c) => c.candidates.length === 0)} empty={<EmptyState title="Nobody in the pipeline yet">Upload CVs to start.</EmptyState>}>
        {(data) => (
          <div className="-mx-4 overflow-x-auto px-4 pb-4">
            <div className="flex gap-3" style={{ minWidth: 'max-content' }}>
              {data.columns.map((col) => (
                <section key={col.stage} aria-label={col.label} className="w-60 shrink-0 rounded-xl bg-muted/50 p-2">
                  <h3 className="flex items-center justify-between px-2 py-1.5 text-small font-medium">
                    {col.label}
                    <span className="rounded-full bg-background px-2 text-small tabular-nums ring-1 ring-foreground/10">{col.candidates.length}</span>
                  </h3>
                  <ul className="space-y-2">
                    {col.candidates.length === 0 && <li className="px-2 py-4 text-center text-small text-muted-foreground">No one here</li>}
                    {col.candidates.map((c) => (
                      <li key={c.id} className="space-y-2 rounded-lg border bg-background p-3 text-small">
                        <Link to={`/candidates/${c.id}`} className="block font-medium hover:underline">{c.full_name}</Link>
                        <p className="truncate text-small text-muted-foreground">{c.current_role || c.external_id}</p>
                        <div className="flex items-center justify-between">
                          {c.band && c.score !== null ? (
                            <span className="flex items-center gap-1.5"><span className="font-semibold tabular-nums">{Math.round(c.score)}</span><BandPill band={c.band} /></span>
                          ) : (
                            <span className="text-small text-muted-foreground">{c.state === 'needs_manual_review' ? 'Manual review' : 'Not scored'}</span>
                          )}
                        </div>
                        {canMove && c.allowed_moves.length > 0 && (
                          <Select
                            aria-label={`Move ${c.full_name}`}
                            value=""
                            disabled={move.isPending}
                            onChange={(e) => e.target.value && move.mutate({ id: c.id, stage: e.target.value as Stage })}
                          >
                            <option value="">Move to…</option>
                            {c.allowed_moves.map((m) => (
                              <option key={m} value={m}>{stageLabel(m)}</option>
                            ))}
                          </Select>
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
