# Infrastructure Standards

Standards for CDK infrastructure code across all OrcaBus pipeline manager services.

## Legacy Cleanup

- Remove all legacy event rules, targets, and placeholder flags (e.g. `isNewWorkflowManagerDeployed` or similar feature flags from the migration period)
- Do not retain commented-out legacy constructs — delete them entirely
- If a service still has legacy orchestration code (pre-WorkflowManager patterns), it must be removed before any new feature work

## Naming Conventions

### Double-Hyphen Separator

All named AWS resources (event rules, step functions, schemas) must use a **double hyphen** (`--`) to separate the stack prefix from the resource name:

```typescript
// Correct
ruleName: `${STACK_PREFIX}--${props.ruleName}`;
stateMachineName: `${STACK_PREFIX}--${props.stateMachineName}`;
schemaName: `${STACK_PREFIX}--${props.schemaName}`;

// Wrong — single hyphen mixes with kebab-case names
ruleName: `${STACK_PREFIX}-${props.ruleName}`;
```

This convention ensures the stack prefix (`orca-<workflow-name>`) is clearly delineated from the resource's logical name.

### Variable Naming in Step Functions

When Step Function definitions use variable names derived from the draft event payload:

- Use `<varName>` directly — do **not** prefix with `draft` (e.g. `projectId`, not `draftProjectId`)
- This keeps the ASL definitions cleaner and avoids confusion about whether the value is still in draft state

```json
// Correct
"projectId.$": "$.data.engineParameters.projectId"

// Wrong — unnecessary draft prefix
"draftProjectId.$": "$.data.engineParameters.projectId"
```

## CDK Patterns

### Lambda Construction

- All Lambdas use `PythonUvFunction` from `@orcabus/platform-cdk-constructs`
- Runtime: Python 3.14, ARM64, 2048 MB memory, 60s timeout (unless documented otherwise)
- One directory per Lambda under `app/lambdas/<snake_case_name>_py/`
- Register in `infrastructure/stage/lambda/interfaces.ts` with IAM requirement flags

### IAM Permissions

- Grant permissions inline in `infrastructure/stage/lambda/index.ts` based on per-Lambda requirement flags
- Always add `NagSuppressions` with a `reason` string justifying any suppression
- Never use wildcard resource ARNs unless absolutely necessary (and suppress with justification)

### Constants

- All constants (SSM paths, event names, bucket names, workflow versions, coverage thresholds) live in `infrastructure/stage/constants.ts`
- Do not hardcode these values elsewhere in the infrastructure code
- Reference data bucket names and test bucket names come from `@orcabus/platform-cdk-constructs/shared-config/s3`
