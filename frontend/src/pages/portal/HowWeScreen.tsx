import { Eye, Lock, Scale, ShieldCheck, UserCheck } from 'lucide-react'
import { Modal } from '@/components/ui/modal'

const POINTS = [
  { icon: Scale, title: 'Blind scoring', text: 'Name, gender, age, photo and marital status are removed from a CV before it is scored.' },
  { icon: Eye, title: 'Every score shows its evidence', text: 'Each criterion quotes the CV. A quote is checked against the CV text; if it cannot be found, it is not shown and the criterion reads “No evidence found”.' },
  { icon: UserCheck, title: 'People decide', text: 'The AI never rejects anyone. A recruiter opens and reviews every CV before submitting it, and you make the decision.' },
  { icon: Lock, title: 'Contacts stay private', text: 'Email and phone are masked until a candidate reaches the interview stage.' },
  { icon: ShieldCheck, title: 'Candidate consent', text: 'CVs are used for hiring only, with consent on record. Candidates can ask for deletion, and every view of a profile is logged.' },
]

export function HowWeScreen({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal open={open} onClose={onClose} title="How we screen" description="What the AI does, what it does not do, and how we keep it fair.">
      <ul className="space-y-4">
        {POINTS.map(({ icon: Icon, title, text }) => (
          <li key={title} className="flex gap-3">
            <Icon className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
            <div>
              <p className="text-sm font-medium">{title}</p>
              <p className="text-sm text-muted-foreground">{text}</p>
            </div>
          </li>
        ))}
      </ul>
      <p className="rounded-lg bg-muted/60 p-3 text-xs text-muted-foreground">
        Scores range 0–100: Strong is 75 and above, Possible is 50–74, Weak is below 50. They help order the reading; they are a guide, not a verdict.
      </p>
    </Modal>
  )
}
