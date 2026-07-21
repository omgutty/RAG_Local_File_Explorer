# Source 03: Test cases (~5,000)

Drop `.csv` / `.xlsx` files here (e.g. `testdata.csv`).

Expected columns (extra columns are fine, all text is indexed):
`Issue Type, Issue Key, Summary, Description, Priority, Component, Labels,
Test Type, Preconditions, Steps, Expected Result, Browser, Device, Status`

Chunking: 1 row = 1 chunk, serialized as `Field: value` lines. The row id
(`Issue Key` / `TC id`) becomes the citation.
