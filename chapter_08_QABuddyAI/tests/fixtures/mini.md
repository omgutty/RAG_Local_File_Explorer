# Handbook

## Bug triage
P1 bugs get an owner within a day. Automation bugs link the Jenkins build.

## Flaky policy
Three intermittent failures put a test in quarantine with the @flaky tag.
Fixed sleeps are banned; use explicit waits everywhere in the framework.
