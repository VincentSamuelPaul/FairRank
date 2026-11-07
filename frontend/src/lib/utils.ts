import { createCn } from 'cn/config'

/** Class merging that knows our token names (type scale and radii), so `text-body` is a size, not a colour. */
export const cn = createCn({
  extend: {
    classGroups: {
      'font-size': [{ text: ['display', 'hero', 'h1', 'h2', 'body', 'small', 'micro'] }],
      rounded: [{ rounded: ['frame', 'card', 'input', 'pill', 'xs'] }],
    },
  },
})
