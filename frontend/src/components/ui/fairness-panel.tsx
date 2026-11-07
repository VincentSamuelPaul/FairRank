import { EyeOff, Quote, Search, ShieldCheck, UserCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

export const RULES = [
  { icon: Quote, lines: ['Every score', 'quotes the CV'], title: 'Every score quotes the CV', text: 'Each criterion shows a line from the CV. The line is checked against the CV text; if it can’t be found it is not shown and the criterion reads “No evidence found”.' },
  { icon: EyeOff, lines: ['Blind to name', 'and gender'], title: 'Blind to name and gender', text: 'Name, gender, age, photo and marital status are removed from a CV before it is scored.' },
  { icon: UserCheck, lines: ['Nobody', 'auto-rejected'], title: 'Nobody is auto-rejected', text: 'The AI never rejects anyone. A recruiter opens and reviews every CV before submitting it, and the client decides.' },
  { icon: Search, lines: ['Low scorers', 'stay searchable'], title: 'Low scorers stay searchable', text: 'Weak scores are labelled, never hidden. Every CV stays in the list and in search.' },
  { icon: ShieldCheck, lines: ['Consent and', 'deletion logged'], title: 'Consent and deletion logged', text: 'CVs are used for hiring only, with consent on record. Candidates can ask for deletion, and every view of a profile is logged.' },
] as const

/** "How we screen": the five rules. `list` for dialogs and the portal, `strip` for the login proof strip. */
export function FairnessPanel({ variant = 'list', className }: { variant?: 'list' | 'strip'; className?: string }) {
  if (variant === 'strip')
    return (
      <ul aria-label="How we screen" className={cn('grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-5', className)}>
        {RULES.map(({ icon: Icon, lines, title }) => (
          <li key={title} aria-label={title} className="flex items-start gap-3">
            <Icon className="mt-0.5 size-5 shrink-0 text-text-1" aria-hidden />
            <span className="text-small leading-snug text-text-1">
              {lines[0]}
              <br />
              {lines[1]}
            </span>
          </li>
        ))}
      </ul>
    )
  return (
    <ul className={cn('space-y-4', className)}>
      {RULES.map(({ icon: Icon, title, text }) => (
        <li key={title} className="flex gap-3">
          <Icon className="mt-0.5 size-5 shrink-0 text-text-1" aria-hidden />
          <div>
            <p className="text-body font-medium">{title}</p>
            <p className="text-small text-text-2">{text}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}
