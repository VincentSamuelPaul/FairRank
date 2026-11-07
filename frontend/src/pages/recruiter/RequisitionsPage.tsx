import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Sparkles } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { z } from 'zod'
import { AppShell, PageHeader } from '@/components/AppShell'
import { Async, EmptyState } from '@/components/states'
import { Button } from '@/components/ui/button'
import { FieldError, Hint, Select, Textarea } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Modal } from '@/components/ui/modal'
import { useMe } from '@/lib/auth'
import { dateOnly, notice, years } from '@/lib/format'
import { useClientOrgs, useCreateRequisition, useRequisitions } from '@/lib/queries'

const EXAMPLE_JD = 'Senior Java Developer, 5-8 years, Spring Boot, Noida, notice up to 60 days'

const schema = z.object({
  client_org: z.string().min(1, 'Choose the client'),
  title: z.string().max(200),
  jd_text: z.string().min(20, 'Paste the job description (at least 20 characters)').max(20000),
})
type Values = z.infer<typeof schema>

function NewRequisition({ open, onClose }: { open: boolean; onClose: () => void }) {
  const orgs = useClientOrgs()
  const create = useCreateRequisition()
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { client_org: '', title: '', jd_text: '' } })

  return (
    <Modal open={open} onClose={onClose} title="New requisition" description="Paste the client’s JD. The AI drafts a scorecard you can edit before any CV is scored.">
      <form
        className="space-y-4"
        noValidate
        onSubmit={handleSubmit((v) =>
          create.mutate(
            { client_org: Number(v.client_org), title: v.title.trim(), jd_text: v.jd_text },
            { onSuccess: (r) => navigate(`/requisitions/${r.requisition.id}/scorecard`, { state: { warning: r.warning, fresh: true } }) },
          ),
        )}
      >
        <div className="space-y-1.5">
          <Label htmlFor="client_org">Client</Label>
          <Select id="client_org" aria-invalid={!!errors.client_org} {...register('client_org')}>
            <option value="">Select a client…</option>
            {orgs.data?.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </Select>
          <FieldError message={errors.client_org?.message} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="title">Title (optional)</Label>
          <Input id="title" placeholder="Taken from the JD if left empty" {...register('title')} />
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="jd_text">Job description</Label>
            <button type="button" className="text-small text-signal hover:underline" onClick={() => setValue('jd_text', EXAMPLE_JD, { shouldValidate: true })}>
              Use the example JD
            </button>
          </div>
          <Textarea id="jd_text" rows={6} aria-invalid={!!errors.jd_text} {...register('jd_text')} />
          <FieldError message={errors.jd_text?.message} />
        </div>
        {create.isError && <FieldError message={create.error.message} />}
        <Button type="submit" className="w-full" disabled={create.isPending}>
          <Sparkles /> {create.isPending ? 'Reading the JD…' : 'Create and draft scorecard'}
        </Button>
        <Hint>Must-haves default to weight 3 and nice-to-haves to 1. You can change both next.</Hint>
      </form>
    </Modal>
  )
}

export function RequisitionsPage() {
  const { data: user } = useMe()
  const query = useRequisitions()
  const [open, setOpen] = useState(false)
  const canEdit = user?.role === 'recruiter'
  return (
    <AppShell>
      <PageHeader
        title="Requisitions"
        subtitle="Upload CVs against a job and see the best first, with reasons."
        actions={
          canEdit && (
            <Button onClick={() => setOpen(true)}>
              <Plus /> New requisition
            </Button>
          )
        }
      />
      <Async
        query={query}
        isEmpty={(d) => d.length === 0}
        empty={
          <EmptyState title="No requisitions yet" action={canEdit && <Button onClick={() => setOpen(true)}>Paste a JD</Button>}>
            Paste a job description to get a scorecard, then upload CVs.
          </EmptyState>
        }
      >
        {(reqs) => (
          <ul className="grid gap-3 sm:grid-cols-2">
            {reqs.map((r) => (
              <li key={r.id}>
                <Link to={`/requisitions/${r.id}`} className="block h-full rounded-card border bg-surface-1 p-5 transition-colors hover:border-primary/50 hover:bg-surface-2">
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="font-medium">{r.title}</h2>
                    <span className="shrink-0 text-small text-muted-foreground">v{r.scorecard_version ?? '–'}</span>
                  </div>
                  <p className="mt-1 text-small text-muted-foreground">
                    {r.client.name}
                    {r.location && ` · ${r.location}`}
                  </p>
                  <p className="text-small text-muted-foreground">
                    {r.exp_min_years !== null && `${years(r.exp_min_years)}–${years(r.exp_max_years)}`}
                    {r.notice_max_days !== null && ` · notice ≤ ${notice(r.notice_max_days)}`}
                  </p>
                  <div className="mt-3 flex gap-4 text-small">
                    <span>
                      <strong className="tabular-nums">{r.counts?.candidates ?? 0}</strong> CVs
                    </span>
                    <span>
                      <strong className="tabular-nums">{r.counts?.submitted ?? 0}</strong> submitted
                    </span>
                    <span className="ml-auto text-small text-muted-foreground">{dateOnly(r.created_at)}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Async>
      <NewRequisition open={open} onClose={() => setOpen(false)} />
    </AppShell>
  )
}
