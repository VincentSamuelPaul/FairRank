import { zodResolver } from '@hookform/resolvers/zod'
import { CalendarClock, Check, X } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { FieldError, Select, Textarea } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Modal } from '@/components/ui/modal'
import { dateTime } from '@/lib/format'
import { usePortalActions } from '@/lib/queries'
import type { ClientCard } from '@/lib/types'

const rejectSchema = z.object({ reason: z.string().trim().min(3, 'Tell the recruiter why, so the next shortlist improves').max(500) })
const slotSchema = z.object({
  starts_at: z.string().min(1, 'Pick a date and time').refine((v) => new Date(v).getTime() > Date.now(), 'Pick a time in the future'),
  duration_minutes: z.coerce.number().int().min(15).max(240),
  note: z.string().max(300),
})

function RejectModal({ card, open, onClose }: { card: ClientCard; open: boolean; onClose: () => void }) {
  const { decide } = usePortalActions(card.id)
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof rejectSchema>>({ resolver: zodResolver(rejectSchema), defaultValues: { reason: '' } })
  return (
    <Modal open={open} onClose={onClose} title={`Reject ${card.full_name}?`} description="A reason is required. It goes to the recruiter, not the candidate.">
      <form className="space-y-3" noValidate onSubmit={handleSubmit((v) => decide.mutate({ decision: 'reject', reason: v.reason }, { onSuccess: onClose }))}>
        <div className="space-y-1.5">
          <Label htmlFor={`reason-${card.id}`}>Reason</Label>
          <Textarea id={`reason-${card.id}`} rows={3} aria-invalid={!!errors.reason} {...register('reason')} />
          <FieldError message={errors.reason?.message} />
        </div>
        <FieldError message={decide.isError ? decide.error.message : undefined} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline"  onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="destructive"  disabled={decide.isPending}>{decide.isPending ? 'Rejecting…' : 'Reject'}</Button>
        </div>
      </form>
    </Modal>
  )
}

function SlotModal({ card, open, onClose }: { card: ClientCard; open: boolean; onClose: () => void }) {
  const { propose } = usePortalActions(card.id)
  type In = z.input<typeof slotSchema>
  const { register, handleSubmit, formState: { errors } } = useForm<In, unknown, z.output<typeof slotSchema>>({
    resolver: zodResolver(slotSchema),
    defaultValues: { starts_at: '', duration_minutes: 30, note: '' },
  })
  return (
    <Modal open={open} onClose={onClose} title="Propose an interview" description={`Suggest a time for ${card.full_name}. Their contact details unlock once you propose.`}>
      <form
        className="space-y-3"
        noValidate
        onSubmit={handleSubmit((v) =>
          propose.mutate({ starts_at: new Date(v.starts_at).toISOString(), duration_minutes: v.duration_minutes, note: v.note }, { onSuccess: onClose }),
        )}
      >
        <div className="space-y-1.5">
          <Label htmlFor={`start-${card.id}`}>Date and time</Label>
          <Input id={`start-${card.id}`} type="datetime-local"  aria-invalid={!!errors.starts_at} {...register('starts_at')} />
          <FieldError message={errors.starts_at?.message} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={`dur-${card.id}`}>Length</Label>
          <Select id={`dur-${card.id}`}  {...register('duration_minutes')}>
            <option value={30}>30 minutes</option>
            <option value={45}>45 minutes</option>
            <option value={60}>1 hour</option>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={`slot-note-${card.id}`}>Note (optional)</Label>
          <Input id={`slot-note-${card.id}`}  placeholder="Panel, video link, location…" {...register('note')} />
        </div>
        <FieldError message={propose.isError ? propose.error.message : undefined} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline"  onClick={onClose}>Cancel</Button>
          <Button type="submit"  disabled={propose.isPending}>{propose.isPending ? 'Sending…' : 'Propose time'}</Button>
        </div>
      </form>
    </Modal>
  )
}

/** Shortlist / propose slot / reject: 48px targets, only what is possible at this stage. Reject opens a bottom sheet for the reason. */
export function DecisionActions({ card }: { card: ClientCard }) {
  const { decide } = usePortalActions(card.id)
  const [reject, setReject] = useState(false)
  const [slot, setSlot] = useState(false)
  const open = card.stage === 'submitted' || card.stage === 'shortlisted'
  const canInterview = open || card.stage === 'interview'
  if (!canInterview) return null
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        {card.stage === 'submitted' && (
          <Button size="lg" className="col-span-2" onClick={() => decide.mutate({ decision: 'shortlist' })} disabled={decide.isPending}>
            <Check /> Shortlist
          </Button>
        )}
        <Button size="lg" variant={card.stage === 'submitted' ? 'secondary' : 'primary'} className={open ? '' : 'col-span-2'} onClick={() => setSlot(true)}>
          <CalendarClock /> {card.stage === 'interview' ? 'Propose another time' : 'Propose slot'}
        </Button>
        {open && (
          <Button size="lg" variant="danger" onClick={() => setReject(true)}>
            <X /> Reject
          </Button>
        )}
      </div>
      <FieldError message={decide.isError ? decide.error.message : undefined} />
      <RejectModal card={card} open={reject} onClose={() => setReject(false)} />
      <SlotModal card={card} open={slot} onClose={() => setSlot(false)} />
    </div>
  )
}

export function DecisionStatus({ card }: { card: ClientCard }) {
  const slot = card.slots.find((s) => s.status !== 'declined')
  if (card.stage === 'rejected')
    return <p className="rounded-input bg-surface-2 p-3 text-small">Rejected{card.decision?.reason && <span className="block text-muted-foreground">Reason: {card.decision.reason}</span>}</p>
  if (slot && ['interview', 'offered', 'joined'].includes(card.stage))
    return (
      <p className="rounded-input bg-surface-2 p-3 text-small">
        Interview proposed for <strong>{dateTime(slot.starts_at)}</strong> · {slot.duration_minutes} min · {slot.status}
        {['offered', 'joined'].includes(card.stage) && <span className="block text-muted-foreground">Now at the {card.stage} stage.</span>}
      </p>
    )
  if (card.stage === 'shortlisted') return <p className="rounded-input bg-surface-2 p-3 text-small">You shortlisted this candidate.</p>
  return null
}
