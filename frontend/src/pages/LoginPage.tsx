import { zodResolver } from '@hookform/resolvers/zod'
import { Info, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm, type UseFormReturn } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { EvidenceQuote } from '@/components/ui/evidence-quote'
import { FairnessPanel } from '@/components/ui/fairness-panel'
import { Field } from '@/components/ui/field'
import { GlassPanel, HairlineRule } from '@/components/ui/glass-panel'
import { Input } from '@/components/ui/input'
import { PillNav } from '@/components/ui/pill-nav'
import { ScoreRing } from '@/components/ui/score-ring'
import { homeFor, useLogin, useMe } from '@/lib/auth'
import { DEMO_ACCOUNTS, DEMO_MODE, DEMO_PASSWORD } from '@/lib/demo'
import { useReducedMotion } from '@/lib/motion'
import type { Band } from '@/lib/types'
import { cn } from '@/lib/utils'

const schema = z.object({
  email: z.string().min(1, 'Enter your email').email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

/* Synthetic candidates (docs/BRIEF.md sample IDs). Names are hidden while scoring (blind scoring). */
type Sample =
  | { id: string; role: string; meta: string; kind: 'scored'; score: number; band: Band; quotes: ({ criterion: string; quote: string } | { criterion: string; none: true })[] }
  | { id: string; role: string; meta: string; kind: 'review' }
const SAMPLES: Sample[] = [
  { id: 'CND-91022', role: 'Senior Java Developer', meta: '6.5 yrs · notice 60 days', kind: 'scored', score: 82, band: 'strong', quotes: [{ criterion: 'Spring Boot', quote: 'Built and maintained 12 Spring Boot microservices' }, { criterion: 'Notice period', quote: 'Notice Period: 60 days' }] },
  { id: 'CND-91088', role: 'Java Developer', meta: '4 yrs · notice 90 days', kind: 'scored', score: 61, band: 'possible', quotes: [{ criterion: 'Hibernate', quote: 'Tuned Hibernate queries and PostgreSQL indexes' }, { criterion: 'Spring Boot', none: true }] },
  { id: 'CND-91103', role: 'KYC Analyst', meta: 'scanned PDF', kind: 'review' },
]
const CYCLE_MS = 7000

/** The sample card choreography: ring fills (900ms), then quotes reveal one after another with a drawn tick (1.2s). */
function SampleBody({ s }: { s: Sample }) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-4">
        {s.kind === 'scored' ? <ScoreRing value={s.score} band={s.band} size="md" stacked ms={900} glow /> : <ScoreRing value={null} state="needs_manual_review" size="md" stacked />}
        <div className="min-w-0 pt-0.5">
          <p className="text-micro uppercase text-text-2">{s.id} · scored blind</p>
          <p className="text-body font-medium">{s.role}</p>
          <p className="text-small text-text-2">{s.meta}</p>
        </div>
      </div>
      {s.kind === 'scored' ? (
        s.quotes.map((q, i) =>
          'none' in q ? (
            <EvidenceQuote key={q.criterion} criterion={q.criterion} status="no_evidence" reveal={900 + i * 600} />
          ) : (
            <EvidenceQuote key={q.criterion} criterion={q.criterion} quote={q.quote} status="verified" reveal={900 + i * 600} />
          ),
        )
      ) : (
        <p className="proof-in rounded-input border border-dashed px-3 py-2 text-small text-text-2" style={{ '--d': '700ms' } as React.CSSProperties}>
          No readable text, so no score. Nobody is rejected: a person reads this CV.
        </p>
      )}
    </div>
  )
}

function ProofStack() {
  const reduced = useReducedMotion()
  const [i, setI] = useState(0)
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (reduced || paused) return
    const t = setInterval(() => setI((n) => (n + 1) % SAMPLES.length), CYCLE_MS)
    return () => clearInterval(t)
  }, [reduced, paused, i])
  return (
    <div className="w-full max-w-sm lg:max-w-md" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div className="relative">
        {/* the card behind peeks out below: honesty about uncertainty */}
        <GlassPanel className="absolute inset-x-4 -bottom-9 top-8 rotate-2 opacity-80" aria-hidden>
          <p className="absolute inset-x-5 bottom-2.5 flex items-center gap-2 text-micro uppercase text-text-2">
            <span className="size-3.5 rounded-pill border-2 border-dashed border-text-2" />
            <span className="max-sm:hidden">CND-91103 · </span>Needs manual review
          </p>
        </GlassPanel>
        <GlassPanel strong rule className="relative -rotate-2 bg-bg-base/55 p-5 pt-6 shadow-float">
          <SampleBody key={i} s={SAMPLES[i]} />
        </GlassPanel>
      </div>
      <div className="mt-12 flex items-center justify-between pl-1">
        <p className="text-micro uppercase text-text-2">Live demo · synthetic data</p>
        <div role="group" aria-label="Sample candidates" className="flex gap-1">
          {SAMPLES.map((s, n) => (
            <button key={s.id} type="button" aria-label={`Show sample ${n + 1} of ${SAMPLES.length}`} aria-pressed={i === n} onClick={() => setI(n)} className="grid size-6 place-items-center">
              <span className={cn('h-1.5 rounded-pill transition-all duration-(--dur-base)', i === n ? 'w-5 bg-text-1' : 'w-1.5 bg-border-strong')} />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function SignInCard({ form }: { form: UseFormReturn<Values> }) {
  const login = useLogin()
  const navigate = useNavigate()
  const { register, handleSubmit, setValue, formState: { errors } } = form
  return (
    <GlassPanel strong className="space-y-4 p-5 max-sm:backdrop-blur-none">
      <h2>Sign in to FairRank</h2>
      <form className="space-y-3.5" noValidate onSubmit={handleSubmit((values) => login.mutate(values, { onSuccess: (u) => navigate(homeFor(u.role), { replace: true }) }))}>
        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="username" className="border-border-strong bg-glass-strong" aria-invalid={!!errors.email} {...register('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" className="border-border-strong bg-glass-strong" aria-invalid={!!errors.password} {...register('password')} />
        </Field>
        {login.isError && <p role="alert" className="text-small text-bad">{login.error.message}</p>}
        {/* on a phone the primary action is pinned to the bottom edge so it is always in thumb reach */}
        <div className="max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-30 max-sm:border-t max-sm:bg-bg-base max-sm:px-(--gutter) max-sm:pb-[calc(0.75rem+var(--safe-bottom))] max-sm:pt-3">
          <Button type="submit" arrow size="lg" className="w-full" loading={login.isPending}>
            {login.isPending ? 'Signing in' : 'Sign in'}
          </Button>
        </div>
      </form>
      {DEMO_MODE && (
        <div className="flex flex-wrap items-center gap-2 border-t pt-3.5">
          <span className="text-micro uppercase text-text-2">Demo</span>
          {DEMO_ACCOUNTS.map((a) => (
            <button
              key={a.email}
              type="button"
              className="inline-flex h-9 items-center rounded-pill border border-border-strong px-3.5 text-small transition-colors duration-(--dur-fast) hover:bg-glass-strong"
              onClick={() => {
                setValue('email', a.email, { shouldValidate: true })
                setValue('password', DEMO_PASSWORD, { shouldValidate: true })
              }}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </GlassPanel>
  )
}

export function LoginPage() {
  const { data: user } = useMe()
  const [dialog, setDialog] = useState<'screen' | 'privacy' | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema) })
  if (user) return <Navigate to={homeFor(user.role)} replace />

  return (
    <div className="min-h-dvh p-(--frame-margin)">
      <div className="showcase-canvas flex min-h-[calc(100dvh-var(--frame-margin)*2)] flex-col gap-6 px-(--gutter) py-5 max-sm:pb-28 md:py-6">
        <div aria-hidden className="showcase-bloom" />
        <header className="flex items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-body font-medium">
            <span className="grid size-9 place-items-center rounded-pill border bg-glass"><ShieldCheck className="size-4" aria-hidden /></span>
            <span className="hidden sm:inline">FairRank</span>
          </p>
          <PillNav items={[{ label: 'How we screen', onClick: () => setDialog('screen') }, { label: 'Privacy', onClick: () => setDialog('privacy') }]} />
          <span className="size-9 max-sm:hidden" aria-hidden />
        </header>

        <main className="grid flex-1 gap-8 lg:grid-cols-[1fr_22rem] lg:grid-rows-[auto_1fr] lg:gap-x-12 lg:gap-y-0">
          <div className="relative z-10 space-y-5 lg:col-start-1 lg:row-start-2 lg:self-end">
            <h1 className="text-hero">
              <span className="text-text-1/70">Hiring that shows </span>
              <span className="text-text-1">its work.</span>
            </h1>
            <p className="max-w-sm text-balance text-small text-text-2">Every score quotes the CV. Low scorers are labelled, never hidden, and nobody is auto-rejected.</p>
          </div>
          <div className="lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:self-center">
            <SignInCard form={form} />
          </div>
          <div className="px-2 pb-10 lg:col-start-1 lg:row-start-1 lg:justify-self-start lg:pb-0 lg:pl-8 lg:pt-4">
            <ProofStack />
          </div>
        </main>

        <footer className="space-y-5">
          <HairlineRule />
          <FairnessPanel variant="strip" />
        </footer>
      </div>

      <Dialog open={dialog === 'screen'} onClose={() => setDialog(null)} title="How we screen" description="What the AI does, what it does not do, and how we keep it fair.">
        <FairnessPanel />
      </Dialog>
      <Dialog open={dialog === 'privacy'} onClose={() => setDialog(null)} title="Privacy" description="CVs are personal data under the DPDP Act 2023.">
        <ul className="space-y-3 text-small text-text-2">
          {[
            'A consent entry is recorded for every candidate, and CVs are used for hiring only.',
            'On request, we delete the CV file, extracted text and parsed fields. A tombstone (ID and date) is kept.',
            'Every view of a profile or CV is logged: who, what and when.',
            'Each client sees only the candidates submitted to them, with contact details masked until the interview stage.',
          ].map((t) => (
            <li key={t} className="flex gap-2"><Info className="mt-0.5 size-4 shrink-0 text-text-1" aria-hidden />{t}</li>
          ))}
        </ul>
      </Dialog>
    </div>
  )
}
