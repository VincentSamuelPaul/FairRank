import * as React from 'react'
import { cn } from '@/lib/utils'

/** Above the control, 13px / 500, secondary text colour. */
function Label({ className, ...props }: React.ComponentProps<'label'>) {
  return <label data-slot="label" className={cn('flex items-center gap-2 text-small font-medium text-text-2 select-none', className)} {...props} />
}

export { Label }
