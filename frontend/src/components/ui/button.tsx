import { Button as ButtonPrimitive } from '@base-ui/react/button'
import { cva, type VariantProps } from 'class-variance-authority'
import { ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'

const secondary =
  'border-border-strong bg-transparent text-text-1 hover:bg-surface-2 aria-expanded:bg-surface-2'
const danger = 'border-border-strong bg-transparent text-bad hover:bg-surface-2'

/** Primary = cream filled pill. Secondary = bordered pill. Ghost = text. Danger = bordered, status colour. */
export const buttonVariants = cva(
  'group/button inline-flex shrink-0 select-none items-center justify-center rounded-pill border border-transparent text-small font-medium whitespace-nowrap transition-[background-color,color,transform] duration-(--dur-fast) ease-ui outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-bad [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=size-])]:size-4',
  {
    variants: {
      variant: {
        default: 'bg-accent text-on-accent hover:opacity-90',
        primary: 'bg-accent text-on-accent hover:opacity-90',
        secondary,
        outline: secondary,
        ghost: 'text-text-1 hover:bg-surface-2 aria-expanded:bg-surface-2',
        danger,
        destructive: danger,
        link: 'rounded-none px-0 text-text-1 underline underline-offset-4 hover:opacity-80',
      },
      size: {
        default: 'h-11 gap-2 px-5',
        lg: 'h-12 gap-2 px-6 text-body',
        sm: 'h-9 gap-1.5 px-4',
        xs: 'h-7 gap-1 px-3 text-micro',
        icon: 'size-11',
        'icon-sm': 'size-9',
        'icon-xs': 'size-7',
        'icon-lg': 'size-12',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

type Props = ButtonPrimitive.Props & VariantProps<typeof buttonVariants> & { arrow?: boolean }

function Button({ className, variant = 'default', size = 'default', arrow = false, children, ...props }: Props) {
  return (
    <ButtonPrimitive data-slot="button" className={cn(buttonVariants({ variant, size, className }))} {...props}>
      {children}
      {arrow && <ArrowRight className="transition-transform duration-(--dur-fast) ease-ui group-hover/button:translate-x-0.5" aria-hidden />}
    </ButtonPrimitive>
  )
}

export { Button }
