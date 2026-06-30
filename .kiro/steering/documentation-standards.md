# Documentation Standards

Standards for README structure and documentation across all OrcaBus pipeline manager services.

## README Structure

Use the [dragen-wgts-dna README](https://github.com/OrcaBus/service-dragen-wgts-dna-pipeline-manager/blob/main/README.md) as the canonical template. Every pipeline manager README must include the following sections in order:

### Required Sections

1. **Title** — `# <Pipeline Name> Pipeline Manager`
2. **Table of Contents** — linked anchors to all sections
3. **Overview** — one-paragraph summary: what the pipeline does, what platform it runs on (ICAv2/CWL), links to CWL releases and platform architecture docs, upstream/downstream services
4. **Pipeline Modes** (if applicable) — table of invocation modes based on input libraries
5. **Pipeline State Flow** — the four state machines with diagrams:
   - DRAFT → populated DRAFT
   - Populated DRAFT → READY
   - READY → ICAv2 submission
   - ICAv2 state changes → WorkflowRunUpdate events
6. **Event Contract** — tables of consumed and published events with detail types, sources, schema links
7. **Draft Event Payload** — minimal DRAFT event example, auto-populated fields table, schema validation link
8. **Submitting a Draft Event** — link to the manual execution SOP
9. **Infrastructure** — stateful resources (schemas, SSM params), stateless resources (Lambdas, Step Functions, EventBridge rules), stack listing
10. **CI/CD and Release Management** — deployment pipeline description
11. **Related Services** — table of upstream, downstream, and dependency services
12. **SOPs** — table linking all operational procedures
13. **Glossary & References** — link to platform glossary, pointer to steering docs for dev setup

### Diagrams

- Store draw.io exports as SVGs under `docs/draw-io-exports/`
- Keep original `.drawio` files under `docs/draw-io-source/` (or equivalent)
- Reference diagrams via relative markdown image links: `![Alt text](docs/draw-io-exports/filename.svg)`

## SOPs

Standard Operating Procedures live under `docs/operation/SOP/` with the naming convention:

```
docs/operation/SOP/
├── README.md                           # Index of all SOPs
├── PM.<ABBREV>.1/
│   └── PM.<ABBREV>.1-ManualPipelineExecution.md
├── PM.<ABBREV>.2/
│   └── PM.<ABBREV>.2-NewPipelineDeployment.md
├── PM.<ABBREV>.3/
│   └── PM.<ABBREV>.3-UpdatingPipelineParameters.md
├── PM.<ABBREV>.4/
│   └── PM.<ABBREV>.4-RunningWorkflowValidations.md
└── PM.<ABBREV>.5/
    └── PM.<ABBREV>.5-TroubleShooting.md
```

Where `<ABBREV>` is a short code for the pipeline (e.g. `DWD` for Dragen WGTS DNA, `OWD` for Oncoanalyser WGTS DNA).

### Minimum SOP Set

Every pipeline manager should have at least:

1. Manual pipeline execution (submitting a DRAFT event)
2. Deploying a new pipeline version
3. Updating SSM parameters
4. Running workflow validations
5. Troubleshooting common issues

## Steering Docs

Each service should have `.kiro/steering/` with:

- Shared standards (these files) — cross-cutting conventions
- `product.md` — service-specific overview, event contract, modes
- `tech.md` — pinned dependency versions, build/test/lint commands
- `structure.md` — service-specific directory layout

The README's final section should point to steering docs for developer setup:

```markdown
## Glossary & References

- Platform glossary: [OrcaBus wiki](https://github.com/OrcaBus/wiki/blob/main/orcabus-platform/README.md#glossary--references)
- For development setup, build commands, project structure, and conventions see the [steering docs](.kiro/steering/).
```
