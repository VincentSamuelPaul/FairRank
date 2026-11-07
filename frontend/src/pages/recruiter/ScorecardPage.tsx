import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useFieldArray, useForm, useWatch } from 'react-hook-form'
import { useLocation, useParams } from 'react-router-dom'
import { z } from 'zod'
import { Async } from '@/components/states'
import { Button } from '@/components/ui/button'
import { FieldError, Hint } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useMe } from '@/lib/auth'
import { useRequisition, useSaveScorecard, useUpdateRequisition } from '@/lib/queries'
import type { Requisition } from '@/lib/types'

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

function Criteria({ req, editable }: { req: Requisition; editable: boolean }) {
  const save = useSaveScorecard(req.id)
  const card = req.scorecard
  const { register, control, handleSubmit, setValue, formState: { errors, isDirty }, reset } = useForm<CriteriaValues>({
    resolver: zodResolver(criteriaSchema),
    defaultValues: { criteria: (card?.criteria ?? []).map(({ name, description, weight, is_must_have }) => ({ name, description, weight, is_must_have })) },
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'criteria' })
  const watched = useWatch({ control, name: 'criteria' }) ?? []
  const totalWeight = watched.reduce((s, c) => s + (Number(c.weight) || 0), 0)
  useEffect(() => {
    if (card) reset({ criteria: card.criteria.map(({ name, description, weight, is_must_have }) => ({ name, description, weight, is_must_have })) })
  }, [card?.id]) // eslint-disable-line react-hooks/exhaustive-deps
  const rootError = (errors.criteria as { root?: { message?: string }; message?: string } | undefined)

  return (
    <form noValidate onSubmit={handleSubmit((v) => save.mutate(v.criteria))} className="space-y-4">
      <ul className="space-y-3">
        {fields.map((f, i) => (
          <li key={f.id} className="grid gap-3 rounded-xl border p-3 sm:grid-cols-[1fr_5.5rem_auto_auto] sm:items-start">
            <div className="space-y-1.5">
              <Label htmlFor={`name-${i}`} className="sr-only">Criterion {i + 1}</Label>
              <Input id={`name-${i}`} placeholder="e.g. Spring Boot" disabled={!editable} aria-invalid={!!errors.criteria?.[i]?.name} {...register(`criteria.${i}.name`)} />
              <Input aria-label={`Description ${i + 1}`} placeholder="What to look for (optional)" disabled={!editable} className="text-muted-foreground" {...register(`criteria.${i}.description`)} />
              <FieldError message={errors.criteria?.[i]?.name?.message} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`weight-${i}`} className="text-small text-muted-foreground">Weight</Label>
              <Input id={`weight-${i}`} type="number" min={1} max={10} disabled={!editable} aria-invalid={!!errors.criteria?.[i]?.weight} {...register(`criteria.${i}.weight`, { valueAsNumber: true })} />
              <FieldError message={errors.criteria?.[i]?.weight?.message} />
            </div>
            <label className="flex h-8 items-center gap-2 text-small sm:mt-5">
              <input
                type="checkbox"
                className="size-4 accent-[var(--primary)]"
                disabled={!editable}
                {...register(`criteria.${i}.is_must_have`, {
                  onChange: (e) => {
                    const w = watched[i]?.weight
                    if (e.target.checked && w === 1) setValue(`criteria.${i}.weight`, 3, { shouldDirty: true })
                    if (!e.target.checked && w === 3) setValue(`criteria.${i}.weight`, 1, { shouldDirty: true })
                  },
                })}
              />
              Must-have
            </label>
            {editable && (
              <Button type="button" variant="ghost" size="icon" className="sm:mt-5" onClick={() => remove(i)} aria-label={`Remove criterion ${i + 1}`}>
                <Trash2 />
              </Button>
            )}
          </li>
        ))}
      </ul>
      <FieldError message={rootError?.message ?? rootError?.root?.message} />
      {editable && (
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" onClick={() => append({ name: '', description: '', weight: 1, is_must_have: false })} disabled={fields.length >= 15}>
            <Plus /> Add criterion
          </Button>
          <Button type="submit" disabled={save.isPending || (!isDirty && !!card)}>
            {save.isPending ? 'Saving…' : `Save as v${(card?.version ?? 0) + 1}`}
          </Button>
          <span className="text-small text-muted-foreground">Total weight {totalWeight}. Saving re-scores every CV against the new version.</span>
        </div>
      )}
      {save.isError && <FieldError message={save.error.message} />}
      {save.isSuccess && (
        <p role="status" className="rounded-lg bg-surface-2 p-3 text-small">
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
