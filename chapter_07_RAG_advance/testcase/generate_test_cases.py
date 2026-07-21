"""Generate 5,000 realistic VWO A/B test cases in JIRA CSV format."""

import sys
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on sys.path so config can be imported
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config import NUM_TEST_CASES

OUTPUT = Path(__file__).parent / "vwo_test_cases_5000.csv"

# ── Domains & modules ──
MODULES = [
    "Landing Page", "Pricing Page", "Checkout Flow", "Signup Flow",
    "Navigation", "Homepage Hero", "Product Page", "Blog Layout",
    "Search Results", "Cart Page", "Payment Modal", "Onboarding",
    "Email Capture", "Footer CTA", "Mobile Menu", "Account Settings",
    "Subscription Flow", "Referral Program", "Exit Intent Popup",
    "Live Chat Widget",
]

TAGS_POOL = [
    "A/B Test", "Multivariate", "Split URL", "Mobile", "Desktop",
    "Tablet", "Traffic: 50/50", "Traffic: 75/25", "Traffic: 90/10",
    "Conversion", "Revenue", "Engagement", "Click-through",
    "Bounce Rate", "Session Duration", "Scroll Depth", "Form Fill",
    "Page Load", "SEO Impact", "Accessibility",
]

PRIORITY_WEIGHTS = {"P0": 0.10, "P1": 0.25, "P2": 0.40, "P3": 0.25}

TEST_SCENARIOS = [
    # ── Landing Page ──
    ("Landing Page", "Test hero headline variant {adj} vs control on landing page",
     "Verify that variant {adj} headline shows within 2s of page load",
     ["1. Navigate to landing page URL with utm_campaign=test_{id}",
      "2. Confirm control headline renders correctly",
      "3. Toggle to variant {adj} via URL param ?variant={letter}",
      "4. Measure render time of variant headline",
      "5. Compare conversion rate over {days}-day period",
      "6. Document statistical significance at 95% confidence"],
     "Variant {adj} headline achieves >= {pct}% lift in conversion over control at 95% significance",
     "P1", "Conversion"),

    ("Landing Page", "Test CTA button color {color1} vs {color2} on hero section",
     "CTA button renders in correct color per variant assignment and is clickable",
     ["1. Load landing page and identify hero CTA button",
      "2. Confirm control shows {color1} CTA",
      "3. Verify variant shows {color2} CTA via cookie/URL assignment",
      "4. Click CTA in both variants and confirm destination URL",
      "5. Track click-through rate over {days} days",
      "6. Run chi-squared test on CTR data"],
     "Variant {color2} CTA shows statistically significant lift >= {pct}% in CTR",
     "P1", "Click-through"),

    # ── Pricing Page ──
    ("Pricing Page", "Test pricing layout {layout_a} vs {layout_b} for tier display",
     "All pricing tiers are visible above the fold on both layouts",
     ["1. Navigate to /pricing on desktop (1920x1080)",
      "2. Confirm control layout {layout_a} shows 3 tiers",
      "3. Toggle to variant {layout_b} via experiment cookie",
      "4. Verify all tier names, prices, and feature lists render",
      "5. Scroll to ensure no content clipping on mobile (375x812)",
      "6. Measure time-to-click on 'Start Free Trial' button"],
     "Variant {layout_b} increases Start Free Trial clicks >= {pct}%",
     "P0", "Revenue"),

    ("Pricing Page", "Test annual vs monthly pricing emphasis on pricing cards",
     "Pricing cards display correct billing frequency labels",
     ["1. Load /pricing page",
      "2. Verify control shows monthly-first pricing",
      "3. Verify variant shows annual-first with 'Save 20%' badge",
      "4. Click annual CTA and confirm checkout shows annual billing",
      "5. Track annual subscription rate over {days} days"],
     "Annual-first variant increases annual subscription rate >= {pct}%",
     "P1", "Revenue"),

    # ── Checkout Flow ──
    ("Checkout Flow", "Test single-page vs multi-step checkout layout",
     "Checkout flow completes end-to-end without errors in both layouts",
     ["1. Add product to cart and proceed to checkout",
      "2. Control: complete checkout across 3 steps (Info → Shipping → Payment)",
      "3. Variant: complete checkout on single scrollable page",
      "4. Verify payment processed and confirmation page shown",
      "5. Measure abandonment rate at each step",
      "6. Compare overall conversion rate"],
     "Single-page variant reduces checkout abandonment >= {pct}%",
     "P0", "Conversion"),

    ("Checkout Flow", "Test guest checkout vs account-required flow",
     "Guest checkout proceeds without forcing account creation",
     ["1. Start checkout without being logged in",
      "2. Control: forced account creation or login",
      "3. Variant: guest checkout with email-only option",
      "4. Complete purchase as guest and confirm order confirmation",
      "5. Measure checkout completion rate per variant",
      "6. Track guest-to-account conversion within 7 days"],
     "Guest checkout variant increases completed purchases >= {pct}%",
     "P1", "Conversion"),

    # ── Signup Flow ──
    ("Signup Flow", "Test social login buttons placement on signup form",
     "Social login buttons (Google, GitHub) render and authenticate correctly",
     ["1. Navigate to signup page",
      "2. Control: social buttons below email form",
      "3. Variant: social buttons above email form",
      "4. Click each social button and complete OAuth flow",
      "5. Verify redirect back to app with authenticated session",
      "6. Track social signup rate over {days} days"],
     "Social-first variant increases signup completion rate >= {pct}%",
     "P1", "Conversion"),

    ("Signup Flow", "Test step-by-step vs single-form signup",
     "Both signup variants collect all required fields correctly",
     ["1. Begin signup process",
      "2. Control: single form with all 6 fields",
      "3. Variant: 3-step wizard (basic → details → confirm)",
      "4. Submit each variant and verify user created in DB",
      "5. Measure time-to-complete for each variant",
      "6. Track dropoff at each step in wizard variant"],
     "Step wizard variant increases signup completion >= {pct}%",
     "P2", "Engagement"),

    # ── Navigation ──
    ("Navigation", "Test mega-menu vs dropdown navigation on desktop",
     "All nav items are accessible within 2 clicks on both variants",
     ["1. Load homepage on desktop",
      "2. Control: hover-triggered dropdown menus",
      "3. Variant: mega-menu with columns and icons",
      "4. Click through all nav items and verify page loads",
      "5. Measure time-to-find specific nav item",
      "6. Track nav item click-through rates"],
     "Mega-menu variant increases nav interaction rate >= {pct}%",
     "P2", "Engagement"),

    ("Navigation", "Test sticky vs static navigation bar",
     "Sticky nav remains visible while scrolling; static nav scrolls with page",
     ["1. Open page and scroll 2000px down",
      "2. Control: nav scrolls with content (static)",
      "3. Variant: nav stays fixed at top (sticky)",
      "4. Click nav item from scrolled position in both variants",
      "5. Measure scroll-to-top time for each variant",
      "6. Track nav CTA click rate from deep-page positions"],
     "Sticky nav increases CTA clicks from scrolled positions >= {pct}%",
     "P2", "Engagement"),

    # ── Homepage Hero ──
    ("Homepage Hero", "Test video hero vs static image hero on homepage",
     "Hero media loads within 3s on both desktop and mobile",
     ["1. Load homepage and observe hero section",
      "2. Control: static background image with headline overlay",
      "3. Variant: autoplay muted video with headline overlay",
      "4. Measure Largest Contentful Paint for both variants",
      "5. Verify video plays correctly on mobile (data-saver)",
      "6. Track bounce rate and time-on-page"],
     "Video hero variant increases time-on-page >= {pct}% without hurting LCP",
     "P1", "Engagement"),

    ("Homepage Hero", "Test personalized hero text vs generic hero",
     "Personalized text reflects user segment (new vs returning)",
     ["1. Clear cookies and load homepage as new visitor",
      "2. Control: generic 'Welcome to our platform' hero",
      "3. Variant: 'Welcome back!' for returning users, tailored for segments",
      "4. Verify correct segment detection via cookie/account",
      "5. Track hero CTA click-through by segment",
      "6. Measure overall homepage conversion lift"],
     "Personalized hero increases CTA clicks from returning users >= {pct}%",
     "P2", "Conversion"),

    # ── Product Page ──
    ("Product Page", "Test social proof count on product page",
     "Social proof counter displays realistic numbers and animates on scroll",
     ["1. Navigate to a product page",
      "2. Control: no social proof in hero section",
      "3. Variant: 'Join 5,000+ customers' counter with logo bar",
      "4. Verify counter animation triggers on scroll into view",
      "5. Confirm all logos are legitimate customer logos",
      "6. Track add-to-cart rate per variant"],
     "Social proof variant increases add-to-cart rate >= {pct}%",
     "P1", "Conversion"),

    ("Product Page", "Test feature tab layout vs accordion layout for product details",
     "All product information is accessible within 3 interactions",
     ["1. Open product detail section",
      "2. Control: horizontal tab layout (Features | Specs | Reviews)",
      "3. Variant: vertical accordion layout",
      "4. Click through each tab/accordion and verify content",
      "5. Measure clicks-to-reach specific info item",
      "6. Track time spent on product details section"],
     "Accordion layout increases engagement with product details >= {pct}%",
     "P2", "Engagement"),

    # ── Blog Layout ──
    ("Blog Layout", "Test grid vs list view for blog archive",
     "All blog posts render and are clickable in both layouts",
     ["1. Navigate to /blog page",
      "2. Control: list layout (full-width posts stacked)",
      "3. Variant: grid layout (3-column card grid)",
      "4. Click through to 3 posts from each layout",
      "5. Measure click-through rate per layout",
      "6. Track average time on article page"],
     "Grid layout increases blog CTR >= {pct}%",
     "P3", "Engagement"),

    ("Blog Layout", "Test estimated reading time badge on blog cards",
     "Reading time displays correctly for all post lengths",
     ["1. View blog archive page",
      "2. Control: no reading time badge",
      "3. Variant: '5 min read' badge on each card",
      "4. Verify badge value matches actual article length",
      "5. Track click-through rate per variant",
      "6. Measure bounce rate per variant"],
     "Reading time badge increases CTR for long-form posts >= {pct}%",
     "P3", "Engagement"),

    # ── Search Results ──
    ("Search Results", "Test instant search vs submit-based search",
     "Instant search shows results within 300ms of user stopping typing",
     ["1. Type search query '/product-name' in search bar",
      "2. Control: press Enter to see results page",
      "3. Variant: dropdown shows results as user types (debounced 300ms)",
      "4. Verify results relevance for partial matches",
      "5. Measure search completion rate per variant",
      "6. Track result click-through rate"],
     "Instant search variant increases search engagement >= {pct}%",
     "P1", "Engagement"),

    # ── Cart Page ──
    ("Cart Page", "Test cart savings summary placement",
     "Savings summary displays accurate discount calculations",
     ["1. Add items worth $100+ to cart",
      "2. Control: savings summary at bottom of cart",
      "3. Variant: savings summary inline next to each item",
      "4. Verify discount calculations match backend",
      "5. Test with 0%, 10%, 25%, 50% discount coupons",
      "6. Track cart-to-checkout conversion"],
     "Inline savings variant increases checkout initiation >= {pct}%",
     "P1", "Revenue"),

    # ── Payment Modal ──
    ("Payment Modal", "Test progress indicator on payment modal",
     "Progress indicator reflects actual step correctly throughout flow",
     ["1. Open payment modal from checkout",
      "2. Control: no progress indicator",
      "3. Variant: 3-step progress bar (Details → Pay → Confirm)",
      "4. Complete payment and verify each step updates",
      "5. Abandon mid-flow and verify no partial charges",
      "6. Track payment completion rate per variant"],
     "Progress indicator variant increases payment completion >= {pct}%",
     "P0", "Conversion"),

    # ── Onboarding ──
    ("Onboarding", "Test progressive onboarding vs full tour",
     "Both onboarding flows complete without errors or confusion",
     ["1. Sign up as new user",
      "2. Control: full product tour (10 steps) shown at once",
      "3. Variant: progressive onboarding (3 steps over 3 sessions)",
      "4. Complete all steps and verify user reaches dashboard",
      "5. Measure activation rate (user completes key action)",
      "6. Track 7-day retention per variant"],
     "Progressive onboarding increases 7-day retention >= {pct}%",
     "P1", "Engagement"),

    # ── Email Capture ──
    ("Email Capture", "Test exit-intent email popup timing",
     "Exit-intent popup triggers only when user intent to leave is detected",
     ["1. Load page and move cursor toward browser close/address bar",
      "2. Control: popup triggers immediately on exit intent",
      "3. Variant A: popup triggers after 3s delay on exit intent",
      "4. Variant B: popup triggers after user scrolls 50% of page",
      "5. Verify popup blocks once submitted (cookie check)",
      "6. Track email capture rate per variant"],
     "Delayed exit-intent popup increases email capture rate >= {pct}%",
     "P2", "Conversion"),

    # ── Footer CTA ──
    ("Footer CTA", "Test footer CTA design variants",
     "Footer CTA is visible without scrolling on short pages",
     ["1. Scroll to bottom of homepage",
      "2. Control: text link 'Get Started' in footer",
      "3. Variant: button-style CTA with gradient background",
      "4. Click CTA and verify landing page",
      "5. Measure click-through rate on mobile vs desktop",
      "6. Track overall conversion from footer CTA"],
     "Button-style footer CTA increases click-through >= {pct}%",
     "P3", "Click-through"),

    # ── Mobile Menu ──
    ("Mobile Menu", "Test hamburger vs bottom nav bar on mobile",
     "Mobile navigation is accessible with thumb-friendly targets",
     ["1. Open site on mobile viewport (375x812)",
      "2. Control: hamburger menu top-left",
      "3. Variant: bottom navigation bar with 5 icons",
      "4. Click each nav item and verify page loads",
      "5. Measure reachability (thumb zone heatmap)",
      "6. Track nav item interaction rate"],
     "Bottom nav bar increases mobile nav interaction rate >= {pct}%",
     "P1", "Engagement"),

    # ── Account Settings ──
    ("Account Settings", "Test inline edit vs modal edit for profile fields",
     "Edits save correctly and reflect immediately in both variants",
     ["1. Navigate to /account/settings",
      "2. Control: click field to open edit modal",
      "3. Variant: click field to make it inline-editable",
      "4. Edit name, email, and company fields",
      "5. Verify changes persist after page refresh",
      "6. Track time-to-edit and save rate"],
     "Inline edit variant reduces time-to-edit profile >= {pct}%",
     "P3", "Engagement"),

    # ── Subscription ──
    ("Subscription Flow", "Test monthly vs annual pricing toggle",
     "Pricing toggle correctly updates all displayed prices",
     ["1. Navigate to /pricing",
      "2. Control: separate monthly and annual tabs",
      "3. Variant: toggle switch with annual 'Save 20%' callout",
      "4. Toggle between billing frequencies and verify prices",
      "5. Select plan and confirm billing period in checkout",
      "6. Track annual plan selection rate"],
     "Toggle variant increases annual plan selection >= {pct}%",
     "P1", "Revenue"),

    # ── Referral ──
    ("Referral Program", "Test referral incentive messaging",
     "Referral code works correctly when applied by referred user",
     ["1. Access referral dashboard as existing user",
      "2. Control: 'Give $10, get $10' message",
      "3. Variant: 'Give 1 month free, get 1 month free' message",
      "4. Copy referral link and open in incognito",
      "5. Complete signup with referral code applied",
      "6. Track referral conversion rate per variant"],
     "Free month variant increases referral signup rate >= {pct}%",
     "P2", "Revenue"),

    # ── Exit Intent ──
    ("Exit Intent Popup", "Test discount offer vs content offer on exit",
     "Offer is relevant and displays correct content per variant",
     ["1. Trigger exit intent on pricing page",
      "2. Control: '10% off' discount offer",
      "3. Variant: 'Free guide: Optimization Tips' content offer",
      "4. Both: dismiss popup and verify no re-trigger within session",
      "5. Track conversion rate (purchase or download)",
      "6. Measure bounce rate impact per variant"],
     "Content offer variant generates more leads at lower cost >= {pct}%",
     "P2", "Conversion"),

    # ── Live Chat ──
    ("Live Chat Widget", "Test proactive vs reactive chat trigger",
     "Chat widget does not interfere with page interaction",
     ["1. Load pricing page and idle for 10s",
      "2. Control: chat icon in bottom-right, user must click",
      "3. Variant: proactive message after 15s idle ('Need help?')",
      "4. Click proactive message and verify chat opens",
      "5. Dismiss chat and verify no re-trigger for 60s",
      "6. Track chat initiation rate and CSAT score"],
     "Proactive chat increases initiated conversations >= {pct}%",
     "P2", "Engagement"),
]

# ── Helpers ──
def pick_priority():
    r = random.random()
    cum = 0
    for p, w in PRIORITY_WEIGHTS.items():
        cum += w
        if r <= cum:
            return p
    return "P2"

def pick_tags():
    return "; ".join(random.sample(TAGS_POOL, k=random.randint(2, 4)))

def fill_template(template, **kwargs):
    return template.format(**kwargs)

def generate_test_cases(n: int):
    rows = []
    used_ids = set()

    adj_pool = ["A", "B", "C"]
    color_pool = ["Blue", "Green", "Orange", "Purple", "Red", "Teal"]
    layout_pool = ["Cards", "Table", "Grid", "List", "Tabs", "Sidebar"]
    pcts = [5, 8, 10, 12, 15, 20, 25]
    days_pool = [7, 14, 21, 30, 60, 90]

    for i in range(1, n + 1):
        scenario = random.choice(TEST_SCENARIOS)
        module, title_tmpl, desc_tmpl, steps_tmpl, expected_tmpl, default_priority, default_tag = scenario

        jira_id = f"VWO-{random.randint(10000, 99999)}"
        while jira_id in used_ids:
            jira_id = f"VWO-{random.randint(10000, 99999)}"
        used_ids.add(jira_id)

        letter = random.choice(["A", "B"])
        adj = random.choice(adj_pool)
        color1 = random.choice(color_pool)
        color2 = random.choice([c for c in color_pool if c != color1])
        layout_a = random.choice(layout_pool)
        layout_b = random.choice([l for l in layout_pool if l != layout_a])
        pct = random.choice(pcts)
        days = random.choice(days_pool)

        fill_kwargs = {
            "id": i,
            "letter": letter,
            "adj": adj,
            "color1": color1,
            "color2": color2,
            "layout_a": layout_a,
            "layout_b": layout_b,
            "pct": pct,
            "days": days,
        }

        title = fill_template(title_tmpl, **fill_kwargs)
        description = fill_template(desc_tmpl, **fill_kwargs)
        steps = [fill_template(s, **fill_kwargs) for s in steps_tmpl]
        expected = fill_template(expected_tmpl, **fill_kwargs)
        priority = default_priority if random.random() < 0.7 else pick_priority()
        tags = f"{default_tag}; {pick_tags()}"

        created = datetime(2025, 1, 1) + timedelta(
            days=random.randint(0, 365),
            hours=random.randint(0, 23)
        )

        rows.append({
            "id": i,
            "jira_id": jira_id,
            "title": title,
            "description": description,
            "preconditions": description,
            "steps": "\n".join(steps),
            "expected": expected,
            "priority": priority,
            "module": module,
            "tags": tags,
            "created_date": created.strftime("%Y-%m-%d"),
        })

    return rows

def main():
    print(f"Generating {NUM_TEST_CASES} VWO test cases...")
    rows = generate_test_cases(NUM_TEST_CASES)

    columns = [
        "id", "jira_id", "title", "description", "preconditions",
        "steps", "expected", "priority", "module", "tags", "created_date",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Generated {len(rows)} test cases -> {OUTPUT}")

if __name__ == "__main__":
    main()
