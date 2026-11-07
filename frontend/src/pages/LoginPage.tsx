import { zodResolver } from '@hookform/resolvers/zod'
import { AlertCircle, Check, Eye, EyeOff, Info, Lock, Mail, ShieldCheck, TriangleAlert, type LucideIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useForm, type UseFormReturn } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { FairnessPanel } from '@/components/ui/fairness-panel'
import { FieldError } from '@/components/ui/field'
import { Label } from '@/components/ui/label'
import { HairlineRule } from '@/components/ui/glass-panel'
import { PillNav } from '@/components/ui/pill-nav'
import { homeFor, useLogin, useMe } from '@/lib/auth'
import { DEMO_ACCOUNTS, DEMO_MODE, DEMO_PASSWORD } from '@/lib/demo'
import { useReducedMotion } from '@/lib/motion'
import { cn } from '@/lib/utils'

const schema = z.object({
  email: z.string().min(1, 'Enter your email').email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

/* Synthetic evidence samples (docs/BRIEF.md). The last one honestly shows the unsure state: no quote, no score. */
type Sample = { criterion: string; quote: string | null }
const SAMPLES: Sample[] = [
  { criterion: 'Spring Boot', quote: 'Built and maintained 12 Spring Boot microservices' },
  { criterion: 'Hibernate', quote: 'Tuned Hibernate queries and PostgreSQL indexes' },
  { criterion: 'Kubernetes', quote: null },
]
const CYCLE_MS = 8000
const FADE_MS = 300

/**
 * The proof line: ONE evidence quote, no card. On load a wash sweeps over the quote (900ms) and the
 * "Verified in CV" tick draws. Every 8s it cross-fades (300ms) to the next sample.
 */
function ProofLine() {
  const reduced = useReducedMotion()
  const [i, setI] = useState(0)
  const [fading, setFading] = useState(false)
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (reduced || paused) return
    let swap: ReturnType<typeof setTimeout>
    const t = setTimeout(() => {
      setFading(true)
      swap = setTimeout(() => { setI((n) => (n + 1) % SAMPLES.length); setFading(false) }, FADE_MS)
    }, CYCLE_MS)
    return () => { clearTimeout(t); clearTimeout(swap) }
  }, [reduced, paused, i])
  const s = SAMPLES[i]
  return (
    <div className="max-w-2xl space-y-3" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <figure key={i} className={cn('space-y-1.5 transition-opacity duration-300 ease-ui', fading ? 'opacity-0' : 'opacity-100')}>
        <figcaption className="text-micro uppercase text-text-2">{s.criterion}</figcaption>
        <blockquote className="text-[20px] leading-snug text-text-1">
          {s.quote ? <span className="proof-wash">“{s.quote}”</span> : <span className="text-text-2">No evidence found</span>}
          {s.quote ? (
            <span className="ml-3 inline-flex items-center gap-1.5 whitespace-nowrap align-middle text-micro uppercase text-text-2">
              <svg aria-hidden viewBox="0 0 12 12" className="tick size-3 text-ok" style={{ '--d': '900ms' } as React.CSSProperties}>
                <path d="M2 6.5 5 9.5 10 3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" pathLength={1} />
              </svg>
              Verified in CV
            </span>
          ) : (
            <span className="ml-3 inline-flex items-center whitespace-nowrap rounded-pill border border-dashed px-2.5 py-0.5 align-middle text-micro uppercase text-text-2">A person reads this CV</span>
          )}
        </blockquote>
      </figure>
      <p className="text-micro text-text-2">Live demo, synthetic data</p>
    </div>
  )
}

const stagger = (n: number) => ({ '--d': `${n * 40}ms` }) as React.CSSProperties

/** Field with a leading icon. The wrapper draws the border so hover, focus and error act on the whole control. */
function LoginField({ id, label, icon: Icon, error, trailing, ...input }: { id: string; label: string; icon: LucideIcon; error?: string; trailing?: React.ReactNode } & React.ComponentProps<'input'>) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="login-field group/field flex items-center gap-3 px-3.5" data-invalid={!!error || input['aria-invalid'] === true || undefined}>
        <Icon aria-hidden className="size-[18px] shrink-0 text-text-3 transition-colors duration-(--dur-instant) group-focus-within/field:text-text-1" />
        <input id={id} aria-invalid={!!error || input['aria-invalid'] || undefined} className="h-full min-w-0 flex-1 text-body outline-none placeholder:text-text-3" {...input} />
        {trailing}
      </div>
      <FieldError message={error} />
    </div>
  )
}

function SignInCard({ form, hold }: { form: UseFormReturn<Values>; hold: (on: boolean) => void }) {
  const login = useLogin()
  const navigate = useNavigate()
  const reduced = useReducedMotion()
  const { register, handleSubmit, setValue, formState: { errors } } = form
  const [show, setShow] = useState(false)
  const [caps, setCaps] = useState(false)
  const [done, setDone] = useState(false)
  const [picked, setPicked] = useState<string | null>(null)
  const submitRef = useRef<HTMLButtonElement>(null)
  const failed = login.isError
  const clear = () => failed && login.reset()
  const email = register('email', { onChange: clear })
  const password = register('password', { onChange: clear })
  const submit = handleSubmit((values) => {
    hold(true) // keep this page up for a beat so the success tick is seen
    login.mutate(values, {
      onSuccess: (u) => { setDone(true); setTimeout(() => navigate(homeFor(u.role), { replace: true }), reduced ? 150 : 650) },
      onError: () => hold(false),
    })
  })
  const lock = (e: React.KeyboardEvent) => setCaps(e.getModifierState?.('CapsLock') ?? false)
  return (
    <div className="login-wrap">
      <div className="login-card fade-up">
        <div className="space-y-1">
          <h2>Welcome back</h2>
          <p className="text-small text-text-2">Sign in to keep screening.</p>
        </div>
        <form className="mt-5 space-y-3.5 sm:mt-6 sm:space-y-4" noValidate onSubmit={submit}>
          {failed && (
            <p key={login.failureCount + String(login.submittedAt)} role="alert" className="shake flex items-center gap-2 rounded-input bg-bad/10 px-3.5 py-2 text-small text-bad">
              <AlertCircle className="size-4 shrink-0" aria-hidden />
              {login.error.message}
            </p>
          )}
          <div className="fade-up" style={stagger(1)}>
            <LoginField id="email" label="Email" icon={Mail} type="email" autoComplete="username" error={errors.email?.message} {...email} aria-invalid={!!errors.email || failed} />
          </div>
          <div className="fade-up" style={stagger(2)}>
            <LoginField
              id="password"
              label="Password"
              icon={Lock}
              type={show ? 'text' : 'password'}
              autoComplete="current-password"
              error={errors.password?.message}
              aria-invalid={!!errors.password || failed}
              onKeyDown={lock}
              onKeyUp={lock}
              onBlur={(e) => { password.onBlur(e); setCaps(false) }}
              name={password.name}
              ref={password.ref}
              onChange={password.onChange}
              trailing={
                <button type="button" aria-label={show ? 'Hide password' : 'Show password'} aria-pressed={show} onClick={() => setShow((v) => !v)} className="-mr-1.5 grid size-9 shrink-0 place-items-center rounded-input text-text-3 transition-colors duration-(--dur-instant) hover:text-text-1">
                  {show ? <EyeOff className="size-[18px]" aria-hidden /> : <Eye className="size-[18px]" aria-hidden />}
                </button>
              }
            />
            {caps && (
              <p role="status" className="mt-1.5 flex items-center gap-1.5 text-small text-warn">
                <TriangleAlert className="size-4 shrink-0" aria-hidden />
                Caps Lock is on
              </p>
            )}
          </div>
          {/* on a phone the primary action is pinned to the bottom edge so it is always in thumb reach */}
          <div className="max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-30 max-sm:border-t max-sm:bg-bg-base max-sm:px-(--gutter) max-sm:pb-[calc(0.75rem+var(--safe-bottom))] max-sm:pt-3 sm:fade-up" style={stagger(3)}>
            <Button ref={submitRef} type="submit" arrow={!done} size="lg" className="h-[52px] w-full" loading={login.isPending && !done}>
              {done ? <><Check aria-hidden className="tick-pop" /> Signed in</> : login.isPending ? 'Signing in' : 'Sign in'}
            </Button>
          </div>
        </form>
        {DEMO_MODE && (
          <div className="fade-up mt-5 space-y-2 border-t pt-4 sm:mt-6 sm:pt-5" style={stagger(4)}>
            <p className="text-micro uppercase text-text-2" id="demo-label">Try a demo role</p>
            <div role="group" aria-labelledby="demo-label" className="space-y-2">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.email}
                  type="button"
                  aria-pressed={picked === a.email}
                  className={cn(
                    'flex min-h-14 w-full flex-col justify-center rounded-[14px] border px-4 py-1.5 text-left lg:min-h-12 transition-colors duration-(--dur-fast) hover:bg-white/5',
                    picked === a.email ? 'border-signal bg-white/5' : 'border-white/10',
                  )}
                  onClick={() => {
                    setPicked(a.email)
                    setValue('email', a.email, { shouldValidate: true })
                    setValue('password', DEMO_PASSWORD, { shouldValidate: true })
                    login.reset()
                    submitRef.current?.focus()
                  }}
                >
                  <span className="text-body text-text-1">{a.label}</span>
                  <span className="text-small text-text-3">{a.blurb}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      <p className="mt-4 flex items-center gap-1.5 px-1 text-micro text-text-3 lg:mt-2.5 lg:absolute lg:inset-x-0 lg:top-full">
        <Lock className="size-3 shrink-0" aria-hidden />
        Every CV view is logged. Candidate data is used for hiring only.
      </p>
    </div>
  )
}

export function LoginPage() {
  const { data: user } = useMe()
  const [dialog, setDialog] = useState<'screen' | 'privacy' | null>(null)
  const [holding, setHolding] = useState(false)
  const form = useForm<Values>({ resolver: zodResolver(schema) })
  if (user && !holding) return <Navigate to={homeFor(user.role)} replace />

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

        <main className="grid flex-1 grid-cols-[minmax(0,1fr)] content-center gap-8 max-lg:gap-10 lg:grid-cols-[minmax(0,1fr)_24rem] lg:items-center lg:gap-x-16">
          <div className="relative z-10 space-y-6">
            <h1 className="text-hero text-text-1">
              Hiring that shows <span className="draw-underline">its work.</span>
            </h1>
            <p className="max-w-sm text-balance text-small text-text-2">Every score quotes the CV. Low scorers are labelled, never hidden, and nobody is auto-rejected.</p>
            <ProofLine />
          </div>
          <SignInCard form={form} hold={setHolding} />
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
