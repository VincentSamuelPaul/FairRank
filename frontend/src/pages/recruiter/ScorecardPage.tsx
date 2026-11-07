import { zodResolver } from '@hookform/resolvers/zod'
import { GripVertical, Minus, Plus, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useFieldArray, useForm, useWatch } from 'react-hook-form'
import { useLocation, useParams } from 'react-router-dom'
import { z } from 'zod'
import { Async } from '@/components/states'
import { Button } from '@/components/ui/button'
import { FieldError, Hint } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useToast } from '@/components/ui/toast'
import { Label } from '@/components/ui/label'
import { useMe } from '@/lib/auth'
import { useRequisition, useSaveScorecard, useUpdateRequisition } from '@/lib/queries'
import type { Requisition } from '@/lib/types'
import { cn } from '@/lib/utils'

const optionalNumber = z.preprocess((v) => (v === '' || v === null || Number.isNaN(v) ? null : Number(v)), z.number().min(0).nullable())

const detailsSchema = z.object({
  location: z.string().max(120),
  exp_min_years: optionalNumber,
  exp_max_years: optionalNumber,
  notice_max_days: optionalNumber,
  ctc_min_lpa: optionalNumber,
  ctc_max_lpa: optionalNumber,
}).refine((v) => v.exp_min_years === null || v.exp_max_years === null || v.exp_min_years <= v.exp_max_years, {
  path: ['exp_max_years'],
  message: 'Maximum must be at least the minimum',
})
type DetailsIn = z.input<typeof detailsSchema>
type DetailsOut = z.output<typeof detailsSchema>

function Details({ req, editable }: { req: Requisition; editable: boolean }) {
  const update = useUpdateRequisition(req.id)
  const { register, handleSubmit, formState: { errors, isDirty }, reset } = useForm<DetailsIn, unknown, DetailsOut>({
    resolver: zodResolver(detailsSchema),
    defaultValues: {
      location: req.location,
      exp_min_years: req.exp_min_years ?? '',
      exp_max_years: req.exp_max_years ?? '',
      notice_max_days: req.notice_max_days ?? '',
      ctc_min_lpa: req.ctc_min !== null ? req.ctc_min / 100000 : '',
      ctc_max_lpa: req.ctc_max !== null ? req.ctc_max / 100000 : '',
    },
  })
  const field = (name: keyof DetailsIn, label: string, props: React.ComponentProps<'input'> = {}) => (
    <div className="space-y-1.5">
      <Label htmlFor={name}>{label}</Label>
      <Input id={name} inputMode="decimal" disabled={!editable} aria-invalid={!!errors[name]} {...register(name)} {...props} />
      <FieldError message={errors[name]?.message as string | undefined} />
    </div>
  )
  return (
    <form
      noValidate
      className="space-y-4"
      onSubmit={handleSubmit((v) =>
        update.mutate(
          {
            location: v.location,
            exp_min_years: v.exp_min_years,
            exp_max_years: v.exp_max_years,
            notice_max_days: v.notice_max_days,
            ctc_min: v.ctc_min_lpa === null ? null : Math.round(v.ctc_min_lpa * 100000),
            ctc_max: v.ctc_max_lpa === null ? null : Math.round(v.ctc_max_lpa * 100000),
          },
          { onSuccess: () => reset(undefined, { keepValues: true }) },
        ),
      )}
    >
      <div className="grid gap-4 sm:grid-cols-3">
        {field('location', 'Location')}
        {field('exp_min_years', 'Experience min (years)')}
        {field('exp_max_years', 'Experience max (years)')}
        {field('notice_max_days', 'Notice up to (days)')}
        {field('ctc_min_lpa', 'CTC min (LPA)')}
        {field('ctc_max_lpa', 'CTC max (LPA)')}
      </div>
      {editable && (
        <div className="flex items-center gap-3">
          <Button type="submit" variant="outline" disabled={!isDirty || update.isPending}>{update.isPending ? 'Saving…' : 'Save details'}</Button>
          {update.isSuccess && !isDirty && <span className="text-small text-muted-foreground">Saved</span>}
          {update.isError && <FieldError message={update.error.message} />}
        </div>
      )}
    </form>
  )
}

const criteriaSchema = z.object({
  criteria: z.array(z.object({
    name: z.string().trim().min(1, 'Name the criterion').max(200),
    description: z.string().max(500),
    weight: z.number('Enter a weight').int().min(1, 'At least 1').max(10, 'At most 10'),
    is_must_have: z.boolean(),
  })).min(1, 'Add at least one criterion').max(15, 'At most 15 criteria'),
}).refine((v) => new Set(v.criteria.map((c) => c.name.trim().toLowerCase())).size === v.criteria.length, {
  path: ['criteria'],
  message: 'Criterion names must be unique',
})
type CriteriaValues = z.infer<typeof criteriaSchema>

type Row = CriteriaValues['criteria'][number]
const MAX_STEP = 5

/** Must-have / Nice-to-have as a two-option toggle. */
function Segmented({ value, onChange, disabled, label }: { value: boolean; onChange: (v: boolean) => void; disabled?: boolean; label: string }) {
  const opt = (on: boolean, text: string) => (
    <button
      type="button"
      role="radio"
      aria-checked={value === on}
      disabled={disabled}
      onClick={() => onChange(on)}
      className={cn('h-9 rounded-pill px-3.5 text-small transition-colors duration-(--dur-fast) disabled:opacity-50', value === on ? 'bg-accent font-medium text-on-accent' : 'text-text-2 hover:text-text-1')}
    >
      {text}
    </button>
  )
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-pill border bg-surface-panel p-0.5">
      {opt(true, 'Must-have')}
      {opt(false, 'Nice-to-have')}
    </div>
  )
}

/** Weight 1 to 5 (the server accepts up to 10; older cards above 5 still display and can be lowered). */
function Stepper({ value, onChange, disabled, label }: { value: number; onChange: (v: number) => void; disabled?: boolean; label: string }) {
  const btn = 'grid size-9 place-items-center rounded-pill border border-border-strong transition-colors duration-(--dur-fast) hover:bg-surface-2 disabled:pointer-events-none disabled:opacity-40'
  return (
    <div role="group" aria-label={`Weight of ${label}`} className="inline-flex items-center gap-1.5">
      <button type="button" className={btn} disabled={disabled || value <= 1} onClick={() => onChange(value - 1)} aria-label={`Decrease weight of ${label}`}><Minus className="size-4" /></button>
      <span className="tnum w-6 text-center text-body font-medium" aria-live="polite">{value}</span>
      <button type="button" className={btn} disabled={disabled || value >= MAX_STEP} onClick={() => onChange(value + 1)} aria-label={`Increase weight of ${label}`}><Plus className="size-4" /></button>
    </div>
  )
}

/** Live: each criterion's share of the total weight (cream = must-have), and how much of the score rides on must-haves. */
function WeightMeter({ rows }: { rows: Row[] }) {
  const total = rows.reduce((t, r) => t + (Number(r.weight) || 0), 0)
  const must = rows.filter((r) => r.is_must_have).reduce((t, r) => t + (Number(r.weight) || 0), 0)
  const pct = total ? Math.round((must / total) * 100) : 0
  return (
    <div className="surface-card space-y-2.5 rounded-card border p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-small font-medium text-text-2">Weights total</p>
        <p className="tnum text-h2">{total}</p>
      </div>
      <div role="img" aria-label={`${rows.length} criteria, total weight ${total}; must-haves carry ${pct}% of the score`} className="flex h-2 gap-0.5 overflow-hidden rounded-pill bg-surface-2">
        {rows.map((r, i) => <span key={i} className={cn('h-full transition-[flex-grow] duration-(--dur-base)', r.is_must_have ? 'bg-accent' : 'bg-text-3')} style={{ flexGrow: Math.max(Number(r.weight) || 0, 0.01) }} />)}
      </div>
      <p className="tnum text-small text-text-2">
        <span className="mr-1 inline-block size-2 rounded-pill bg-accent align-baseline" aria-hidden /> Must-haves carry {pct}% of the score
        <span className="mx-2" aria-hidden>·</span>
        <span className="mr-1 inline-block size-2 rounded-pill bg-text-3 align-baseline" aria-hidden /> Nice-to-haves {100 - pct}%
      </p>
    </div>
  )
}

function Criteria({ req, editable }: { req: Requisition; editable: boolean }) {
  const save = useSaveScorecard(req.id)
  const { toast } = useToast()
  const card = req.scorecard
  const { register, control, handleSubmit, setValue, getValues, formState: { errors, isDirty }, reset } = useForm<CriteriaValues>({
    resolver: zodResolver(criteriaSchema),
    defaultValues: { criteria: (card?.criteria ?? []).map(({ name, description, weight, is_must_have }) => ({ name, description, weight, is_must_have })) },
  })
  const { fields, append, remove, move, insert } = useFieldArray({ control, name: 'criteria' })
  const watched = useWatch({ control, name: 'criteria' }) ?? []
  const [dragFrom, setDragFrom] = useState<number | null>(null)
  const [over, setOver] = useState<number | null>(null)
  const armed = useRef(false)
  useEffect(() => {
    if (card) reset({ criteria: card.criteria.map(({ name, description, weight, is_must_have }) => ({ name, description, weight, is_must_have })) })
  }, [card?.id]) // eslint-disable-line react-hooks/exhaustive-deps
  const rootError = errors.criteria as { root?: { message?: string }; message?: string } | undefined

  const setMust = (i: number, must: boolean) => {
    setValue(`criteria.${i}.is_must_have`, must, { shouldDirty: true })
    const w = watched[i]?.weight
    if (must && w === 1) setValue(`criteria.${i}.weight`, 3, { shouldDirty: true })
    if (!must && w === 3) setValue(`criteria.${i}.weight`, 1, { shouldDirty: true })
  }
  const drop = (i: number) => {
    const removed = getValues(`criteria.${i}`)
    remove(i)
    toast(`Removed “${removed.name || 'criterion'}”`, 'info', { label: 'Undo', onClick: () => insert(i, removed) })
  }

  return (
    <form noValidate onSubmit={handleSubmit((v) => save.mutate(v.criteria))} className="space-y-4">
      <WeightMeter rows={watched as Row[]} />
      <ul className="space-y-3">
        {fields.map((f, i) => (
          <li
            key={f.id}
            draggable={editable}
            onDragStart={(e) => {
              if (!armed.current) return e.preventDefault()
              setDragFrom(i)
              e.dataTransfer.effectAllowed = 'move'
            }}
            onDragOver={(e) => {
              if (dragFrom === null) return
              e.preventDefault()
              setOver(i)
            }}
            onDrop={(e) => {
              e.preventDefault()
              if (dragFrom !== null && dragFrom !== i) move(dragFrom, i)
              setDragFrom(null)
              setOver(null)
            }}
            onDragEnd={() => {
              armed.current = false
              setDragFrom(null)
              setOver(null)
            }}
            className={cn('surface-card grid gap-3 rounded-card border p-4 transition-[border-color,opacity] duration-(--dur-fast) sm:grid-cols-[auto_1fr_auto] sm:items-start', over === i && dragFrom !== i && 'border-signal', dragFrom === i && 'opacity-50')}
          >
            <button
              type="button"
              disabled={!editable}
              aria-label={`Reorder criterion ${i + 1}: drag, or press the up and down arrow keys`}
              onPointerDown={() => { armed.current = true }}
              onPointerUp={() => { armed.current = false }}
              onKeyDown={(e) => {
                if (e.key === 'ArrowUp' && i > 0) { e.preventDefault(); move(i, i - 1) }
                if (e.key === 'ArrowDown' && i < fields.length - 1) { e.preventDefault(); move(i, i + 1) }
              }}
              className="hidden size-9 cursor-grab place-items-center rounded-input text-text-2 hover:bg-surface-2 hover:text-text-1 active:cursor-grabbing disabled:opacity-40 sm:grid"
            >
              <GripVertical className="size-5" aria-hidden />
            </button>
            <div className="space-y-2">
              <Label htmlFor={`name-${i}`} className="sr-only">Criterion {i + 1}</Label>
              <Input id={`name-${i}`} placeholder="e.g. Spring Boot" disabled={!editable} aria-invalid={!!errors.criteria?.[i]?.name} {...register(`criteria.${i}.name`)} />
              <Input aria-label={`Description ${i + 1}`} placeholder="What to look for (optional)" disabled={!editable} className="h-10 border-transparent bg-transparent text-small text-text-2 hover:border-border focus-visible:bg-surface-2" {...register(`criteria.${i}.description`)} />
              <FieldError message={errors.criteria?.[i]?.name?.message ?? errors.criteria?.[i]?.weight?.message} />
            </div>
            <div className="flex flex-wrap items-center gap-3 sm:justify-end">
              <Segmented label={`Importance of criterion ${i + 1}`} value={!!watched[i]?.is_must_have} disabled={!editable} onChange={(v) => setMust(i, v)} />
              <Stepper label={watched[i]?.name || `criterion ${i + 1}`} value={Number(watched[i]?.weight) || 1} disabled={!editable} onChange={(w) => setValue(`criteria.${i}.weight`, w, { shouldDirty: true, shouldValidate: true })} />
              {editable && (
                <Button type="button" variant="ghost" size="icon-sm" onClick={() => drop(i)} aria-label={`Remove criterion ${i + 1}`}>
                  <Trash2 />
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
      <FieldError message={rootError?.message ?? rootError?.root?.message} />
      {editable && (
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="secondary" onClick={() => append({ name: '', description: '', weight: 1, is_must_have: false })} disabled={fields.length >= 15} disabledReason="A scorecard can have at most 15 criteria">
            <Plus /> Add criterion
          </Button>
          <Button type="submit" loading={save.isPending} disabled={!isDirty && !!card} disabledReason="No changes to save yet">
            {save.isPending ? 'Saving' : `Save as v${(card?.version ?? 0) + 1}`}
          </Button>
          <span className="text-small text-text-2">Saving re-scores every CV against the new version.</span>
        </div>
      )}
      {save.isError && <FieldError message={save.error.message} />}
      {save.isSuccess && (
        <p role="status" className="rounded-input border bg-surface-1 p-3 text-small">
          Saved as v{save.data.version}. {save.data.rescoring > 0 ? `Re-scoring ${save.data.rescoring} CVs now.` : 'No CVs to re-score yet.'}
        </p>
      )}
    </form>
  )
}

export function ScorecardPage() {
  const { id = '' } = useParams()
  const { data: user } = useMe()
  const location = useLocation()
  const state = location.state as { warning?: string; fresh?: boolean } | null
  const query = useRequisition(id)
  const [showJd, setShowJd] = useState(false)
  const editable = user?.role === 'recruiter'
  return (
    <Async query={query}>
      {(req) => (
        <div className="space-y-8">
          {state?.warning && <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-small">{state.warning}</p>}
          {state?.fresh && !state.warning && (
            <p className="flex items-start gap-2 rounded-lg bg-surface-2 p-3 text-small">
              <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              Drafted from the JD. Check the criteria, weights and must-haves before you upload CVs: the AI can miss or over-read things.
            </p>
          )}
          <section className="space-y-3">
            <h2 className="font-medium">Role details</h2>
            <Details key={req.id + req.scorecard_version} req={req} editable={editable} />
          </section>
          <section className="space-y-3">
            <div>
              <h2 className="font-medium">Scoring criteria {req.scorecard && <span className="font-normal text-muted-foreground">· v{req.scorecard.version}, {req.scorecard.source === 'ai' ? 'drafted by AI' : 'edited by a recruiter'}</span>}</h2>
              <Hint>Must-haves default to weight 3, nice-to-haves to 1. Each CV gets 0–100 per criterion; the total is the weighted average. Every edit makes a new version, so old scores stay explainable.</Hint>
            </div>
            <Criteria key={req.scorecard?.id ?? 'none'} req={req} editable={editable} />
          </section>
          <section>
            <button type="button" className="text-small text-signal hover:underline" onClick={() => setShowJd((s) => !s)} aria-expanded={showJd}>
              {showJd ? 'Hide' : 'Show'} the original job description
            </button>
            {showJd && <p className="mt-2 whitespace-pre-wrap rounded-lg bg-muted/60 p-3 text-small">{req.jd_text}</p>}
          </section>
        </div>
      )}
    </Async>
  )
}
