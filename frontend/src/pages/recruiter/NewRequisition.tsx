import { zodResolver } from '@hookform/resolvers/zod'
import { AlertCircle, Check, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Spinner } from '@/components/states'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Hint, Textarea } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Listbox } from '@/components/ui/listbox'
import { Monogram } from '@/components/ui/monogram'
import { useClientOrgs, useCreateRequisition } from '@/lib/queries'
import { cn } from '@/lib/utils'

export const EXAMPLE_JD = 'Senior Java Developer, 5-8 years, Spring Boot, Noida, notice up to 60 days'

const schema = z.object({
  client_org: z.string().min(1, 'Choose the client'),
  title: z.string().max(200),
  jd_text: z.string().min(20, 'Paste the job description (at least 20 characters)').max(20000),
})
type Values = z.infer<typeof schema>

/** The order the server works in. It answers once, so the first three are estimated; the last completes only when the draft is really ready. */
const STEPS = ['Reading the JD', 'Finding must-haves', 'Setting weights', 'Checking against the JD']

type Phase = 'form' | 'drafting' | 'failed'

function Steps({ done }: { done: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-5">
      <div className="h-1 overflow-hidden rounded-pill bg-surface-2" role="progressbar" aria-valuemin={0} aria-valuemax={STEPS.length} aria-valuenow={done} aria-label="Drafting progress">
        <div className="h-full rounded-pill bg-signal transition-[width] duration-(--dur-base) ease-ui" style={{ width: `${(done / STEPS.length) * 100}%` }} />
      </div>
      <ol className="space-y-3">
        {STEPS.map((label, i) => {
          const state = i < done ? 'done' : i === done ? 'active' : 'todo'
          return (
            <li key={label} className={cn('flex items-center gap-3 text-body', state === 'todo' && 'text-text-3')}>
              <span className="grid size-6 place-items-center">
                {state === 'done' ? <Check className="size-4 text-ok" aria-hidden /> : state === 'active' ? <Spinner className="size-4 text-signal" /> : <span aria-hidden className="size-2 rounded-pill border border-text-3" />}
              </span>
              <span className={cn(state === 'active' && 'font-medium')}>{label}</span>
              <span className="sr-only">{state === 'done' ? 'done' : state === 'active' ? 'in progress' : 'waiting'}</span>
            </li>
          )
        })}
      </ol>
      <Hint>Progress is an estimate: the server reports once, when the draft is ready (usually under 20 seconds).</Hint>
    </div>
  )
}

export function NewRequisition({ open, onClose }: { open: boolean; onClose: () => void }) {
  const orgs = useClientOrgs()
  const create = useCreateRequisition()
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('form')
  const [done, setDone] = useState(0)
  const [made, setMade] = useState<string | null>(null) // id of a requisition the server created without a scorecard
  const [reason, setReason] = useState('')
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { client_org: '', title: '', jd_text: '' } })
  const { control, register, handleSubmit, setValue, getValues, formState: { errors } } = form

  useEffect(() => {
    if (!open) {
      setPhase('form')
      setDone(0)
      setMade(null)
      setReason('')
    }
  }, [open])
  useEffect(() => {
    if (phase !== 'drafting') return
    const t = setInterval(() => setDone((d) => Math.min(d + 1, STEPS.length - 1)), 1600)
    return () => clearInterval(t)
  }, [phase])

  const draft = (v: Values) => {
    setPhase('drafting')
    setDone(0)
    setMade(null)
    create.mutate(
      { client_org: Number(v.client_org), title: v.title.trim(), jd_text: v.jd_text },
      {
        onSuccess: (r) => {
          if (r.warning) {
            setMade(r.requisition.id)
            setReason(r.warning)
            setPhase('failed')
            return
          }
          setDone(STEPS.length)
          setTimeout(() => {
            navigate(`/requisitions/${r.requisition.id}/scorecard`, { state: { fresh: true } })
            onClose()
          }, 700)
        },
        onError: (e) => {
          setReason(e.message)
          setPhase('failed')
        },
      },
    )
  }

  const title = phase === 'form' ? 'New requisition' : phase === 'drafting' ? 'Drafting your scorecard' : 'Couldn’t draft the scorecard'
  return (
    <Dialog open={open} onClose={onClose} wide title={title} description={phase === 'form' ? 'Paste the client’s JD. The AI drafts a scorecard you can edit before any CV is scored.' : undefined}>
      <p className="text-micro uppercase text-text-2">Step {phase === 'form' ? 1 : 2} of 2 · {phase === 'form' ? 'Client and JD' : 'Scorecard'}</p>

      {phase === 'form' && (
        <form className="space-y-5" noValidate onSubmit={handleSubmit(draft)}>
          <Field label="Client" htmlFor="client_org" error={errors.client_org?.message}>
            <Controller
              control={control}
              name="client_org"
              render={({ field }) => (
                <Listbox
                  id="client_org"
                  value={field.value}
                  onChange={field.onChange}
                  invalid={!!errors.client_org}
                  placeholder={orgs.isPending ? 'Loading clients…' : 'Select a client'}
                  options={(orgs.data ?? []).map((o) => ({ value: String(o.id), label: o.name, icon: <Monogram name={o.name} className="size-7 text-micro" /> }))}
                />
              )}
            />
          </Field>
          <Field label="Title (optional)" htmlFor="title" hint="Taken from the JD if left empty.">
            <Input id="title" placeholder="e.g. Senior Java Developer" {...register('title')} />
          </Field>
          <Field
            label="Job description"
            htmlFor="jd_text"
            error={errors.jd_text?.message}
            aside={
              <button
                type="button"
                onClick={() => setValue('jd_text', EXAMPLE_JD, { shouldValidate: true, shouldDirty: true })}
                className="inline-flex h-8 items-center gap-1.5 rounded-pill border border-border-strong px-3 text-small text-signal transition-colors duration-(--dur-fast) hover:bg-surface-2"
              >
                <Sparkles className="size-3.5" aria-hidden /> Use the example JD
              </button>
            }
          >
            <Controller control={control} name="jd_text" render={({ field }) => <Textarea id="jd_text" showCount maxLength={20000} placeholder="Paste the job description here" aria-invalid={!!errors.jd_text} {...field} />} />
          </Field>
          <Button type="submit" size="lg" arrow className="w-full">Draft scorecard</Button>
          <Hint>Must-haves default to weight 3 and nice-to-haves to 1. You can change both next.</Hint>
        </form>
      )}

      {phase === 'drafting' && <Steps done={done} />}

      {phase === 'failed' && (
        <div role="alert" className="space-y-4">
          <div className="flex items-start gap-3 rounded-card border border-bad/40 bg-surface-panel p-4">
            <AlertCircle className="mt-0.5 size-5 shrink-0 text-bad" aria-hidden />
            <div className="space-y-1">
              <p className="text-body font-medium">The scorecard was not drafted</p>
              <p className="text-small text-text-2">{reason}</p>
              {made && <p className="text-small text-text-2">The requisition itself was saved. Trying again makes a fresh draft and leaves this empty one in your list.</p>}
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button className="sm:flex-1" arrow onClick={() => draft(getValues())}>Try again</Button>
            {made ? (
              <Button variant="secondary" className="sm:flex-1" onClick={() => { navigate(`/requisitions/${made}/scorecard`, { state: { warning: reason, fresh: true } }); onClose() }}>
                Build the scorecard manually
              </Button>
            ) : (
              <Button variant="secondary" className="sm:flex-1" onClick={() => setPhase('form')}>Back to the form</Button>
            )}
          </div>
        </div>
      )}
    </Dialog>
  )
}
