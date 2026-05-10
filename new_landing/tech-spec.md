# Replikor — Technical Specification

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.2.0 | UI framework |
| react-dom | ^18.2.0 | DOM renderer |
| typescript | ^5.3.0 | Type safety |
| vite | ^5.0.0 | Build tool |
| tailwindcss | ^3.4.19 | Utility CSS |
| three | ^0.160.0 | WebGL scenes (Ambient Glow + MSDF Text) |
| gsap | ^3.12.0 | Animation engine, ScrollTrigger, SplitText |
| @studio-freight/lenis | ^1.1.0 | Smooth scroll |
| three-msdf-text-utils | ^1.0.0 | MSDF text mesh for Typography Reveal |
| msdf-bmfont-xml | ^2.7.0 | MSDF font atlas generator (dev dependency) |

**Google Fonts** (loaded via `<link>` in index.html): Manrope (400–700), Inter (400–500), IBM Plex Mono (400–500)

---

## Component Inventory

### Layout

| Component | Source | Reuse |
|-----------|--------|-------|
| FixedHeader | Custom | Once — glassmorphic nav with scroll-driven padding shrink |
| Footer | Custom | Once |
| MobileNav | Custom | Once — slide-in hamburger drawer |

### Sections

| Component | Source | Notes |
|-----------|--------|-------|
| HeroSection | Custom | Video bg + overlay + text + trust bar |
| TypographyRevealSection | Custom | Three.js MSDF text with scroll-driven fill |
| ProblemSection | Custom | Sticky 2-col + 2×2 problem cards |
| HowItWorksSection | Custom | Sticky 2-col + 3-tab chat preview |
| MetricsReportSection | Custom | 3×2 metric cards with animated score bars |
| ForManagersSection | Custom | Sticky 2-col + CEO quote + 6 insight cards |
| ScenariosSection | Custom | Sticky 2-col + asymmetric tag grid |
| PilotSection | Custom | 5-step wave timeline + CTA |
| DemoFormSection | Custom | Sticky 2-col + grouped form card |
| FAQSection | Custom | Accordion list |

### Reusable Components

| Component | Source | Used By |
|-----------|--------|---------|
| SectionLabel | Custom | All sections — uppercase mono label with accent color |
| GradientButton | Custom | Header, Hero, Pilot, Form — mint-to-cyan gradient CTA |
| GhostButton | Custom | Header, Hero — outlined secondary CTA |
| GlassCard | Custom | Problem, Metrics, Managers, HowItWorks — glassmorphic card surface |
| MetricCard | Custom | MetricsReportSection — score + progress bar + status color |
| ScenarioTag | Custom | ScenariosSection — hoverable tag pill |
| StepCard | Custom | PilotSection — numbered step in wave layout |
| FAQItem | Custom | FAQSection — accordion item |

### Hooks

| Hook | Purpose |
|------|---------|
| useScrollEntrance | GSAP ScrollTrigger fade+translateY entrance on ref mount |
| useLenis | Initialize Lenis smooth scroll, wire to ScrollTrigger |

---

## Animation Implementation

| Animation | Library | Approach | Complexity |
|-----------|---------|----------|------------|
| Typography Reveal Scroll (MSDF text fill) | three + gsap/ScrollTrigger | MSDF text mesh with custom fragment shader; `uProgress` uniform scrubbed 0→1 via GSAP ScrollTrigger on pinned container. Character-fill wave + stroke-to-fill transition. | **High** 🔒 |
| Ambient Glow System | three + gsap/ScrollTrigger | 3 Three.js planes with custom radial gradient shaders. GSAP timeline with scrub drives `uCenter`, `uOpacity`, `position` uniforms per layer across full page scroll. Fixed canvas at z-index 0. | **High** 🔒 |
| Hero video background | Native `<video>` | autoplay muted loop playsinline, object-fit cover. CSS gradient overlay div above. | Low |
| Section entrance (fade + translateY) | gsap/ScrollTrigger | Shared useScrollEntrance hook: opacity 0→1, y 24→0, triggered at `top 80%`. All sections reuse. | Low |
| Card stagger entrance | gsap/ScrollTrigger | Batch cards with 0.1s stagger, y 32→0, 0.5s each. Triggered once per section. | Low |
| Metric score count-up | gsap | `gsap.to()` target object, `{ duration: 1, ease: "power2.out", snap: { value: 1 } }`, onUpdate writes to DOM. Triggered by ScrollTrigger. | Low |
| Metric progress bar fill | gsap/ScrollTrigger | `scaleX(0→1)` with transform-origin left, 1s ease-out, triggered on scroll entry. | Low |
| Pilot step wave reveal | gsap/ScrollTrigger | 5 steps fade-in left-to-right, 0.15s stagger. Steps 2,4 have inline `translateY(-24px)`. | Low |
| Header scroll shrink | gsap/ScrollTrigger | ScrollTrigger watches hero scroll; toggles compact padding class (16px→12px). | Low |
| Tab content switch | gsap | Content div opacity 1→0→1, 0.25s ease. No layout shift. | Low |
| FAQ expand/collapse | CSS | `max-height` transition 0.3s ease + content opacity 0.2s. Toggle class. | Low |
| Card hover lift | CSS | `translateY(-4px)`, shadow deepen, border brighten. Pure CSS transition 0.3s. | Low |
| Scroll indicator bounce | CSS | `translateY(0→8px)`, 2s ease-in-out infinite. Pure CSS keyframes. | Low |
| Button hover (ghost) | CSS | `background: rgba(255,255,255,0.06)`, 0.2s ease. | Low |
| Nav link hover | CSS | Color `#94a3b8` → `#e2e8f0`, 0.2s ease. | Low |
| Scenario tag hover | CSS | bg `#131d32` → `#232d42`, `scale(1.02)`, 0.2s ease. | Low |
| Input focus glow | CSS | Border-color → `#5eead4`, `box-shadow: 0 0 0 3px rgba(94,234,212,0.1)`. | Low |

---

## State & Logic Plan

### Three.js ↔ React Bridge (Ambient Glow)

The Ambient Glow runs as a **persistent fixed background** across the entire page lifecycle. It must:
- Be created once on mount and shared across all sections
- Read scroll position from GSAP ScrollTrigger (not React state) to avoid 60fps re-renders
- Handle resize via `ResizeObserver` on the window/body
- Be destroyed on unmount

Approach: A single `AmbientGlow` component at the App root level creates its own `THREE.WebGLRenderer` with `alpha: true`, renders to a fixed-position `<canvas>`, and uses GSAP ScrollTrigger callbacks to update shader uniforms directly (bypassing React state entirely).

### Three.js ↔ React Bridge (Typography Reveal)

The Typography Reveal is an **isolated section-level** Three.js scene:
- Created when the section mounts, destroyed when it unmounts
- Owns its renderer, scene, camera, and MSDF text mesh
- The scroll-driven `uProgress` uniform is updated via GSAP ScrollTrigger `onUpdate` callback, writing directly to `mesh.material.uniforms.uProgress.value` — no React re-renders
- Resize handling re-creates renderer dimensions

### Lenis ↔ GSAP ScrollTrigger Integration

Lenis must be initialized **before** any ScrollTrigger instances. On each Lenis scroll event, call `ScrollTrigger.update()`. This is a one-time setup in a `useLenis` hook at the App level.

### Form State

The demo form has 7 fields (text, email, select, textarea, checkbox). All managed with local `useState`. No form library needed — on submit, log to console (no backend).

### Mobile Detection

The Typography Reveal effect and Ambient Glow (reduced to 1 layer) need viewport-width gating. Use a `useMediaQuery` hook (or CSS media queries where possible) to conditionally render/disable effects. Check `window.innerWidth < 768` on mount and on resize.

---

## Other Key Decisions

### Raw Three.js (not @react-three/fiber)

The design specifies manual renderer setup with explicit shader code, orthographic camera, and low-level uniform manipulation. Both Three.js scenes are imperative and scroll-driven — raw Three.js avoids R3F's declarative overhead and gives direct control over the render loop, which is critical for the 60fps scroll-synced shader updates.

### No shadcn/ui Components

All UI elements in this design are custom-styled glassmorphic components with specific dark-theme aesthetics. Using shadcn/ui primitives would require overriding nearly all default styles. Custom implementations are more consistent and lighter.

### MSDF Font Atlas

The Typography Reveal requires a pre-generated MSDF atlas for Manrope Bold (700). The `msdf-bmfont-xml` CLI tool generates a `.png` atlas + `.json` glyph data file as a build step. These assets are placed in `public/fonts/` and loaded at runtime by `three-msdf-text-utils`. The atlas must be generated before the first build.

### Video Asset

The hero video is a generated 5s seamless loop. It is placed in `public/videos/` as an MP4/WebM file. A static first-frame JPEG fallback is provided for browsers that block autoplay. The video uses `playsinline muted autoplay loop` attributes.
