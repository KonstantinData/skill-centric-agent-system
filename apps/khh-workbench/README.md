# KHH Workbench

Next.js workbench for the Kinderhaus Heuschrecken tenant on
`kinderhaus-heuschrecken.cloud`.

The app exposes a Leitung-, Fristen-, Risiko-, Aufgaben- und
Entwicklungs-Cockpit for `kinderhaus`. It must not become a master-data
system for children, parents, or staff.

## Product Boundary

The visible workflow surface is limited to:

- Heute dashboard for daily leadership status
- Fristen and Nachweise with risk and due-date focus
- Personal-Ampel for operational coverage risk
- Dienste for Kochdienst, Arbeitseinsaetze, and Elternpflichten
- Vorgaenge for protected incident and follow-up handling
- Belegung and Entwicklung planning without full person records
- Dokumente and Aufgaben as controlled references and work layers

The app must only show person references as first names, initials, role labels,
or internal references. It must not show surnames, private contact data,
addresses, birth dates, contract data, diagnosis details, personnel files, or
full child, parent, or staff records.

## Product Language Boundary

Visible copy is German and must describe leadership work, risks, deadlines,
approval needs, and next actions. It must not expose internal SCAS architecture
terms, runtime profile composition, validators, policies, tenant isolation
mechanics, or implementation evidence.

Users must not see or infer that other tenants exist. KHH content must not use
foreign tenant sources, fixtures, examples, or workflow labels.

## Design Surface

The interface follows the KHH design guideline:

- warm yellow and green brand cues
- paper-like surfaces and restrained natural tones
- compact leadership dashboard density
- status chips with text, never color alone
- no marketing landing page
- no decorative child-app treatment inside work views

## Local Validation

```powershell
npm --prefix apps/khh-workbench run lint
npm --prefix apps/khh-workbench run build
```
