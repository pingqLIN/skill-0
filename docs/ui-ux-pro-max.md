---
description: Plan and implement UI
auto_execution_mode: 3
constraints: ui-design-constraints.json
---

# UI/UX Pro Max - Design Intelligence

Searchable database of UI styles, color palettes, font pairings, chart types, product recommendations, UX guidelines, and stack-specific best practices.

## Design Philosophy Constraints

> **Priority**: Cognitive load reduction  
> **UI Role**: Deferential to content  
> **Novelty**: Not allowed - use system conventions

## Prerequisites

Check if Python is installed:

```bash
python3 --version || python --version
```

If Python is not installed, install it based on user's OS:

**macOS:**

```bash
brew install python3
```

**Ubuntu/Debian:**

```bash
sudo apt update && sudo apt install python3
```

**Windows:**

```powershell
winget install Python.Python.3.12
```

---

## How to Use This Workflow

When user requests UI/UX work (design, build, create, implement, review, fix, improve), follow this workflow:

### Step 1: Analyze User Requirements

Extract key information from user request:

- **Product type**: SaaS, e-commerce, portfolio, dashboard, landing page, etc.
- **Style keywords**: minimal, professional, elegant, dark mode (avoid playful/novelty styles)
- **Industry**: healthcare, fintech, gaming, education, etc.
- **Stack**: React, Vue, Next.js, or default to `html-tailwind`

### Step 2: Search Relevant Domains

Use `search.py` multiple times to gather comprehensive information. Search until you have enough context.

```bash
python3 .shared/ui-ux-pro-max/scripts/search.py "<keyword>" --domain <domain> [-n <max_results>]
```

**Recommended search order:**

1. **Product** - Get style recommendations for product type
2. **Style** - Get detailed style guide (colors, effects, frameworks)
3. **Typography** - Get font pairings with Google Fonts imports
4. **Color** - Get color palette (Primary, Secondary, CTA, Background, Text, Border)
5. **Landing** - Get page structure (if landing page)
6. **Chart** - Get chart recommendations (if dashboard/analytics)
7. **UX** - Get best practices and anti-patterns
8. **Stack** - Get stack-specific guidelines (default: html-tailwind)

### Step 3: Stack Guidelines (Default: html-tailwind)

If user doesn't specify a stack, **default to `html-tailwind`**.

```bash
python3 .shared/ui-ux-pro-max/scripts/search.py "<keyword>" --stack html-tailwind
```

Available stacks: `html-tailwind`, `react`, `nextjs`, `vue`, `svelte`, `swiftui`, `react-native`, `flutter`, `shadcn`

---

## Search Reference

### Available Domains

| Domain | Use For | Example Keywords |
|--------|---------|------------------|
| `product` | Product type recommendations | SaaS, e-commerce, portfolio, healthcare, beauty, service |
| `style` | UI styles, colors, effects | minimalism, dark mode, neutral (avoid glassmorphism, brutalism) |
| `typography` | Font pairings, Google Fonts | professional, modern, system-like |
| `color` | Color palettes by product type | saas, ecommerce, healthcare, beauty, fintech, service |
| `landing` | Page structure, CTA strategies | hero, hero-centric, testimonial, pricing, social-proof |
| `chart` | Chart types, library recommendations | trend, comparison, timeline, funnel, pie |
| `ux` | Best practices, anti-patterns | animation, accessibility, z-index, loading |
| `prompt` | AI prompts, CSS keywords | (style name) |

### Available Stacks

| Stack | Focus |
|-------|-------|
| `html-tailwind` | Tailwind utilities, responsive, a11y (DEFAULT) |
| `react` | State, hooks, performance, patterns |
| `nextjs` | SSR, routing, images, API routes |
| `vue` | Composition API, Pinia, Vue Router |
| `svelte` | Runes, stores, SvelteKit |
| `swiftui` | Views, State, Navigation, Animation |
| `react-native` | Components, Navigation, Lists |
| `flutter` | Widgets, State, Layout, Theming |
| `shadcn` | shadcn/ui components, theming, forms, patterns |

---

## Example Workflow

**User request:** "Lam landing page cho dich vu cham soc da chuyen nghiep"

**AI should:**

```bash
# 1. Search product type
python3 .shared/ui-ux-pro-max/scripts/search.py "beauty spa wellness service" --domain product

# 2. Search style (based on industry: beauty, elegant)
python3 .shared/ui-ux-pro-max/scripts/search.py "elegant minimal soft" --domain style

# 3. Search typography
python3 .shared/ui-ux-pro-max/scripts/search.py "elegant luxury" --domain typography

# 4. Search color palette
python3 .shared/ui-ux-pro-max/scripts/search.py "beauty spa wellness" --domain color

# 5. Search landing page structure
python3 .shared/ui-ux-pro-max/scripts/search.py "hero-centric social-proof" --domain landing

# 6. Search UX guidelines
python3 .shared/ui-ux-pro-max/scripts/search.py "animation" --domain ux
python3 .shared/ui-ux-pro-max/scripts/search.py "accessibility" --domain ux

# 7. Search stack guidelines (default: html-tailwind)
python3 .shared/ui-ux-pro-max/scripts/search.py "layout responsive" --stack html-tailwind
```

**Then:** Synthesize all search results and implement the design.

---

## Tips for Better Results

1. **Be specific with keywords** - "healthcare SaaS dashboard" > "app"
2. **Search multiple times** - Different keywords reveal different insights
3. **Combine domains** - Style + Typography + Color = Complete design system
4. **Always check UX** - Search "animation", "z-index", "accessibility" for common issues
5. **Use stack flag** - Get implementation-specific best practices
6. **Iterate** - If first search doesn't match, try different keywords
7. **Split Into Multiple Files** - For better maintainability:
   - Separate components into individual files (e.g., `Header.tsx`, `Footer.tsx`)
   - Extract reusable styles into dedicated files
   - Keep each file focused and under 200-300 lines

---

## Design Constraints (from ui-design-constraints.json)

### Layout

| Constraint | Value | Rationale |
|------------|-------|-----------|
| **Preferred flow** | Single column vertical | Reduces cognitive load |
| **Max primary actions** | 1 per screen | Clear next step |
| **Use whitespace** | Yes | Typography/spacing over decoration |
| **Decorative dividers** | Avoid | Minimalist approach |

### Navigation

| Constraint | Value |
|------------|-------|
| **Allowed patterns** | `navigation_bar`, `tab_bar`, `sheet`, `modal`, `push_pop` |
| **Custom navigation** | Not allowed |
| **Back action** | Required |
| **Directional consistency** | Required |

### Typography

| Constraint | Value |
|------------|-------|
| **Text is interface** | Yes - prefer text over icons |
| **Icons** | Optional, not primary |
| **System hierarchy** | Use system font hierarchy |
| **Dense text** | Avoid |

### Color

| Constraint | Value |
|------------|-------|
| **Color role** | Functional only (interaction/state) |
| **Max accent colors** | 1 |
| **Structure colors** | Neutral |
| **Saturation** | Low saturation preferred (default) |
| **Dark mode** | Requires recalculation |

### Components

| Constraint | Value |
|------------|-------|
| **Standard components** | Preferred |
| **Decorative elements** | Not allowed |
| **Cards** | Only for hierarchy, not decoration |

### Motion

| Constraint | Value |
|------------|-------|
| **Animation causality** | Required (cause-and-effect) |
| **Directional motion** | Required |
| **Attention-seeking motion** | Not allowed |

### Error Handling

| Constraint | Value |
|------------|-------|
| **Error messages** | Must be actionable |
| **Memory dependency** | Not allowed (user shouldn't need to remember) |

### Decision Fallback

> When uncertain, choose the **least visually assertive option** that remains functional.

---

## Common Rules for Professional UI

These are frequently overlooked issues that make UI look unprofessional:

### Icons & Visual Elements

| Rule | Do | Don't |
|------|----|----- |
| **Text-first approach** | Use clear text labels | Rely on icons alone |
| **No emoji icons** | Use SVG icons (Heroicons, Lucide, Simple Icons) | Use emojis like :art: as UI icons |
| **Stable hover states** | Use color/opacity transitions on hover | Use scale transforms that shift layout |
| **Correct brand logos** | Research official SVG from Simple Icons | Guess or use incorrect logo paths |
| **Consistent icon sizing** | Use fixed viewBox (24x24) with w-6 h-6 | Mix different icon sizes randomly |

### Interaction & Cursor

| Rule | Do | Don't |
|------|----|----- |
| **Cursor pointer** | Add `cursor-pointer` to all clickable/hoverable cards | Leave default cursor on interactive elements |
| **Hover feedback** | Provide visual feedback (color, shadow, border) | No indication element is interactive |
| **Smooth transitions** | Use `transition-colors duration-200` | Instant state changes or too slow (>500ms) |
| **Single accent color** | Use one accent for all interactive elements | Multiple accent colors in same view |

### Light/Dark Mode Contrast

| Rule | Do | Don't |
|------|----|----- |
| **Glass card light mode** | Use `bg-white/80` or higher opacity | Use `bg-white/10` (too transparent) |
| **Text contrast light** | Use `#0F172A` (slate-900) for text | Use `#94A3B8` (slate-400) for body text |
| **Muted text light** | Use `#475569` (slate-600) minimum | Use gray-400 or lighter |
| **Border visibility** | Use `border-gray-200` in light mode | Use `border-white/10` (invisible) |
| **Recalculate for dark mode** | Adjust all colors for dark context | Simply invert or use same values |

### Layout & Spacing

| Rule | Do | Don't |
|------|----|----- |
| **Single column preferred** | Use vertical flow for main content | Complex multi-column layouts |
| **Floating navbar** | Add `top-4 left-4 right-4` spacing | Stick navbar to `top-0 left-0 right-0` |
| **Content padding** | Account for fixed navbar height | Let content hide behind fixed elements |
| **Consistent max-width** | Use same `max-w-6xl` or `max-w-7xl` | Mix different container widths |
| **Whitespace over borders** | Use spacing to separate sections | Decorative dividers and borders |

---

## Pre-Delivery Checklist

Before delivering UI code, verify these items:

### Cognitive Load (Priority)

- [ ] Single primary action per screen is obvious
- [ ] Next step is immediately clear
- [ ] No unnecessary elements (would removing it harm understanding?)
- [ ] Consistent with system-level UI expectations

### Visual Quality

- [ ] Text used as primary interface (icons are supplementary)
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] Brand logos are correct (verified from Simple Icons)
- [ ] Hover states don't cause layout shift
- [ ] Only one accent color used

### Interaction

- [ ] All clickable elements have `cursor-pointer`
- [ ] Hover states provide clear visual feedback
- [ ] Transitions are smooth (150-300ms)
- [ ] Focus states visible for keyboard navigation

### Light/Dark Mode

- [ ] Light mode text has sufficient contrast (4.5:1 minimum)
- [ ] Glass/transparent elements visible in light mode
- [ ] Borders visible in both modes
- [ ] Dark mode colors recalculated (not just inverted)
- [ ] Test both modes before delivery

### Layout

- [ ] Single column vertical flow preferred
- [ ] Floating elements have proper spacing from edges
- [ ] No content hidden behind fixed navbars
- [ ] Responsive at 320px, 768px, 1024px, 1440px
- [ ] No horizontal scroll on mobile
- [ ] Whitespace used instead of decorative dividers

### Navigation

- [ ] Only standard patterns used (nav bar, tab bar, sheet, modal, push/pop)
- [ ] No custom navigation patterns
- [ ] Back action available where needed
- [ ] Directional consistency maintained

### Motion

- [ ] Animations have clear cause-and-effect
- [ ] Directional logic is consistent
- [ ] No attention-seeking animations

### Error Handling

- [ ] Error messages are actionable
- [ ] User doesn't need to remember previous states

### Accessibility

- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Color is not the only indicator
- [ ] `prefers-reduced-motion` respected
