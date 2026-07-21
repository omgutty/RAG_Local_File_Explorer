# Sprint 42 planning notes (2026-07-10)

[00:02] Pramod: Top priority this sprint is stabilizing the checkout suite. applyCouponTest is flaky on about 30% of nightly runs, tracked as VWO-2002.
[00:05] Priya: The root cause is the coupon banner loading asynchronously. I will replace the Thread.sleep calls with explicit waits on presenceOfElementLocated and add the @flaky quarantine tag until the fix lands.
[00:09] Rahul: Reminder that per our flaky test policy, three consecutive intermittent failures means quarantine plus an owner. I am taking VWO-2002.
[00:11] Rahul: Second item, the RTM needs updating for the new A/B goal tracking section in the PRD (section 4). VWO-2003 added regression cases TC-3321 and TC-3322, they must be linked to requirement R-114.
[00:14] Pramod: Coverage target for the payment module is 80% this quarter. Current Copilot-assisted flow gets us roughly 30-40%; once QABuddy RAG context is wired into reviews we expect 70-80%.
[00:18] Priya: For onboarding, the two new joiners should self-serve from QABuddy instead of pinging seniors: framework setup, locator conventions, and how to run the nightly suite.
[00:21] Pramod: Action items: Priya fixes VWO-2002 waits, Rahul updates RTM for R-114, everyone reviews the login error toast failure from Jenkins build #128 before Thursday.
