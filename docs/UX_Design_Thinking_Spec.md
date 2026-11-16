# CampusLoop UX Design Thinking Specification

## Product intent and boundaries

CampusLoop is a demo platform for extending the useful life of campus goods through senior resale, day transfer, TrustLend borrowing, and dealer pooling. It helps students make a practical next choice without implying that estimates are guaranteed or that a recorded bid or payout transfers money. All currency is displayed in Indian rupees.

This prototype has no authentication, identity provider, payment provider, or real-world dealer verification. Student IDs are seeded demo identifiers, not proof of identity. QR tokens and handovers simulate an application flow and do not verify that two people met. Dealer records marked verified are demo data. Purchases, payouts, and TrustLend handovers are simulated records only; no actual charge, UPI, payment, or disbursement occurs. Estimates and allocations are arithmetic examples, not guaranteed outcomes.

## Design principles

1. **Make the next action legible.** Each item has a recognizable category, condition, block, price, and clear reuse path. Forms use plain labels and inline feedback. Filters retain their chosen values and expose an honest empty state.
2. **Use trust as an earned, explainable signal.** Trust score and TrustLend eligibility are shown with a numeric score and state, not color alone. Explain that demo student IDs do not constitute identity verification.
3. **Separate estimates from outcomes.** Resale, day-transfer, pool, and scrap estimates remain visibly distinct. A submitted demo dealer bid is an offer in the prototype; a final allocation is labeled simulated and is not a payment guarantee.
4. **Support a calm, accessible interaction.** Use a warm off-white canvas, white cards, muted sage/teal accents, soft sand surfaces, readable dark text, and restrained coral warnings. Preserve semantic headings, labeled controls, keyboard focus, status announcements, readable contrast, reduced-motion support, and persistent Lite mode.
5. **Keep personal agency.** Request camera access only after an explicit scan action. Offer a clearly named demo-scan action, never presented as a verified physical handoff.

## Motion direction

The home story takes inspiration from the [Floema sustainability scroll interaction](https://www.awwwards.com/inspiration/sustainability-scroll-interaction-floema), listed as scroll, WebGL, and illustration. Its sustainability narrative moves through product imagery and material chapters. CampusLoop translates that staged, illustrated storytelling into a light SVG reuse loop: one book icon follows a drawn path while the four reuse cards take focus. It uses no WebGL scene or external artwork.

GSAP ScrollTrigger pins the four-card story on wide screens and scrubs the illustration and card focus with scroll progress. Lenis runs through the GSAP ticker only when the wide-screen animation is active. Narrow screens, Lite mode, and `prefers-reduced-motion` retain the complete unpinned story, stop optional smoothing, and show the static loop. The SVG uses current CampusLoop design tokens; no motion state communicates an API, identity, or payment result.

## UX frameworks

### Design Thinking: five phases

- **Empathize:** Learn from graduating residents who need to clear usable belongings, hostel residents seeking affordable short-term essentials, and campus dealer agents who need legible batch and bid records. Observe their device, time, accessibility, and trust constraints rather than assuming them.
- **Define:** Frame the problem as helping campus participants choose a suitable next life for an item—resale, day transfer, temporary lending, or pooled dealer sale—while understanding eligibility, estimates, and simulated outcomes.
- **Ideate:** Explore connected page journeys, an explainable valuation, exact category and block filters, a zero-price TrustLend path, one-time QR token display with alternatives, four guarded dealer stages, clear status feedback, and low-bandwidth/reduced-motion options.
- **Prototype:** Build five linked static pages—home, valuation, marketplace, TrustLend, and dealer pool—with a shared light visual system. The standalone editable SVG supplies desktop and mobile page-layout artboards. Keep interactions and financial/identity boundaries explicit.
- **Test:** Test task completion and comprehension with representative users. Include keyboard-only navigation, narrow and wide viewports, reduced motion, Lite mode, camera denial, API outage, empty states, valuation boundaries, purchase replay/unavailability, borrow/return timing, and dealer-stage guards. Check that users can distinguish a demo from a real identity check or transfer.

### Peter Morville's UX honeycomb

Design and evaluate each page against all seven facets:

- **Useful:** Supports real campus reuse decisions across resale, short transfer, lending, and pooling.
- **Usable:** Offers predictable navigation, understandable forms, readable output, and recoverable actions.
- **Desirable:** Uses a calm, welcoming light palette and respectful language without distracting decoration.
- **Findable:** Provides consistent shared navigation, recognizable page titles, meaningful labels, and category/block filters.
- **Accessible:** Supports semantic structure, keyboard operation, visible focus, contrast, responsive layouts, reduced motion, and announced status changes.
- **Credible:** Distinguishes estimates from bids and simulation from real-world payment, identity, or handover verification.
- **Valuable:** Helps students keep goods in use and makes the system's value to campus residents and participating demo roles understandable.

### Five usable-product characteristics

- **Effective:** Users can complete the intended task—understand an estimate, list or buy an item, request/return a loan, or progress a dealer batch.
- **Efficient:** Common paths have clear defaults and avoid unnecessary steps; persistent filters and role selections reduce repeated input.
- **Engaging:** Friendly, specific content and restrained motion make campus reuse understandable without obscuring the task.
- **Error tolerant:** Validate input, prevent invalid/replayed stage actions, explain unavailable or ineligible states, and retain entered information where possible.
- **Easy to learn:** Use familiar page structures, consistent terminology, visible stage names, and contextual explanations for trust and demo statuses.

### Five interaction-design dimensions

- **Words:** Plain action labels and explanatory microcopy, including “simulated” where appropriate; avoid jargon and financial guarantees.
- **Visual representations:** Cards, status badges, estimates, trust ring, QR token, stage indicators, and simple layout hierarchy communicate state without relying on color alone.
- **Physical objects and space:** The responsive page works on desktop and mobile; camera permission and QR scanning are optional interactions with the physical world, not requirements for using the demo.
- **Time:** Show loading and expiry states, the 24-hour one-time handover token, seven-day due interval/countdown, and the consequences of stage progression.
- **Behavior:** Controls provide predictable feedback, preserve selection where possible, prevent invalid/replayed actions, and provide alternatives when camera, network, or motion support is unavailable.

### Double Diamond

- **Discover:** Map the lifecycle of textbooks, appliances, and furniture across a semester and listen for friction in listing, finding, borrowing, and disposal.
- **Define:** Focus on keeping usable goods moving with transparent, local, low-effort interactions.
- **Develop:** Compare individual resale, day transfer, TrustLend, and pooled dealer outcomes; test them with the personas below.
- **Deliver:** Deliver the five-page prototype with visible API, empty, loading, and error feedback; iterate from task completion and comprehension.

### Jobs to be Done

- “When I am moving out, help me understand what this item could be worth and choose a path that avoids needless waste.”
- “When I need one thing for a short time, help me borrow it with a clear return date and an explainable trust signal.”
- “When individual listings are not worthwhile, help me combine useful goods and understand the dealer's total bid and simulated allocation.”

## Personas

### Aanya — graduating senior, Block A
Aanya is packing for the end of term and has textbooks, a lamp, and an appliance to pass on. She wants to clear her room quickly, earn a fair amount when resale is practical, and avoid sending working goods to waste. She is comfortable with mobile forms but distrusts prices that appear as guarantees.

**Needs:** Quick ISBN-assisted book entry, understandable estimated values, easy block-local filters, and an explicit difference between estimate and confirmed demo bid.

**Design response:** Valuation page, optional ISBN lookup, marketplace listing flow, category/block filters, and distinct estimate and bid labels.

### Kabir — hostel borrower, Block C
Kabir arrived with limited supplies and needs an occasional calculator or appliance without committing to a purchase. He wants to know whether borrowing is possible, when it is due, and how a return affects the community. He is cautious about sharing personal data or installing another app.

**Needs:** No-cost borrowing, clear time limits, a familiar QR handover, and simple trust eligibility without overstated identity checks.

**Design response:** TrustLend page with borrower/lender roles, seeded demo-student selection, one-time expiring token, opt-in camera, typed-token/demo handover alternatives, visible countdown, and return confirmation.

### Meera — campus dealer agent, Block B
Meera coordinates a move-out collection with campus dealer agents. Many usable items have modest individual value, and residents ask how a bulk dealer offer will be shared. She needs a simple way to collect items, compare bids, and explain the record to owners.

**Needs:** Batch membership and per-item estimates, highest-first bids, predictable guarded stage transitions, and a transparent allocation record.

**Design response:** Dealer pool page with item-level pool/scrap comparisons, the four named stages, demo dealer bids, winning-bid display, and owner allocation marked “simulated payout only.”

## Five-page experience

- **Home (`index.html`):** Introduces the reuse story and four paths, with clear navigation and optional motion-led storytelling. Motion does not gate content.
- **Valuation (`valuation.html`):** Labeled controls show resale, day-transfer, trust/eligibility, pool, and scrap estimates; ISBN lookup is optional.
- **Marketplace (`marketplace.html`):** Exact category, mode, and block filters support browsing; item cards identify owner and availability. Listing, checkout, buyer/seller identity, and history are explicit demo workflows.
- **TrustLend (`trustlend.html`):** Borrower selects a demo student and eligible item; lender is derived from the item's owner. Loan history shows participant roles, due/return timing, and trust changes. QR display is paired with readable token fallback and optional scanning.
- **Dealer pool (`dealer-pool.html`):** Shows entries, owners, estimate comparisons, ranked demo bids, winner, guarded transitions, and simulated allocation. The four display stages are exactly **Hostel Pickup Scheduled**, **Pooled in Campus Batch**, **Wholesale Dealer Auction Won**, and **Payout Recorded (Simulated)**.

All pages share navigation and design tokens. Direct static-page navigation and refresh should work without a client-side router. Unknown paths should present a visible not-found fallback. Provide persistent labeled inputs, visible loading/empty/error/offline feedback, responsive layouts, reduced-motion behavior, and accessible high contrast. The home storytelling sequence may use GSAP/ScrollTrigger pinning and scrub on capable desktop layouts only; disable pinning on narrow screens and when reduced motion is preferred. Lite mode pauses nonessential motion and reports only a client-side bandwidth estimate; third-party CDN assets may already have downloaded.

## Gitflow branch instructions

Preserve the non-destructive behavior in `docs/gitflow-init.sh`: run it from a clean Git worktree after an initial commit. It creates missing branches without overwriting existing branches and switches to `develop`. The exact branch names are `main`, `develop`, `feature/valuation-engine`, `feature/trustlend-qr`, `feature/dealer-pool`, and `feature/gsap-ui`.

## Interaction, accessibility, and demo requirements

- Primary navigation and all actions are keyboard operable with a visible focus indicator. Dialogs have labels, an accessible name, Escape and close controls, and return focus to their trigger.
- Form controls have persistent labels; validation and network errors are announced through live regions. Loading and empty states remain visible instead of silently disappearing.
- High contrast is a persistent toggle. Lite mode persists, reduces nonessential animation, and stops smooth-scroll timelines; `prefers-reduced-motion` takes precedence over motion effects.
- Camera scanning begins only on explicit user request and stops when the dialog closes, token is read, or page is left. Denied camera permission never blocks manual token handling or the labeled simulation.
- Do not use color as the only indicator of eligibility, online status, winning bid, or stage. Include text and numeric signals.
- Student selectors identify demo records only and are not authentication. QR tokens do not prove identity or physical handover. Purchases and dealer allocations do not charge, transfer, or disburse real money; no UPI or payment transfer occurs.
- Bandwidth savings are a client-side estimate only. Third-party CDN assets may already have downloaded; Lite mode does not claim to undo that transfer.

## Evaluation questions

1. Can a student identify the four reuse paths and explain that pool and scrap numbers are estimates?
2. Can a borrower start, activate, and return a loan without enabling a camera—and understand the QR is a demo token rather than verified identity?
3. Can an owner determine what the highest total dealer bid means and distinguish a simulated allocation from an actual payment?
4. Can users complete these tasks at narrow mobile widths, under reduced-motion settings, and with API/network errors announced clearly?
5. Can a user find the correct page and understand the four dealer stages without relying on color or prior instruction?
