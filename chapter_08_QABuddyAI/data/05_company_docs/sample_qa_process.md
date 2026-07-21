# QA Process Handbook (excerpt)

## Bug triage
- Severity levels: P1 blocks release or core user flow, P2 major feature degraded with workaround, P3 minor, P4 cosmetic.
- Every new bug is triaged within 24 hours by the module owner; P1 gets an owner immediately and a daily status update.
- Bugs found by automation must link the failing test name and the Jenkins build number.

## Test design
- Every PRD section maps to test cases in the RTM (Requirements Traceability Matrix); coverage gaps are reviewed weekly.
- Test cases follow the standard template: Title, Preconditions, Steps, Expected Result, Priority, Tags.
- New features require at least one negative and one boundary test per acceptance criterion.

## Flaky test policy
- Three consecutive intermittent failures -> the test gets the @flaky quarantine tag and an owner.
- Quarantined tests run in a separate non-blocking Jenkins stage and must be fixed within the sprint.
- Fixed sleeps (Thread.sleep / waitForTimeout) are banned in framework code; use explicit waits.

## Definition of done for a bug fix
- Root cause documented on the JIRA ticket.
- Regression test added and linked in the RTM.
- Green nightly run including the new test.
