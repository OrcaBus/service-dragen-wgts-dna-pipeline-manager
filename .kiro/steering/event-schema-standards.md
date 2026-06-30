# Event Schema Standards

Standards for event schema registration and validation across all OrcaBus pipeline manager services.

## Schema Location

Event schemas belong in the **stateful stack** and are stored under the `app/` directory:

```
app/
└── event-schemas/
    └── complete-data-draft/
        └── <payload-version>/
            └── complete-data-draft-schema.json
```

### Versioned Directory Structure

Schemas are versioned by payload version (e.g. `2025.06.04`). The directory structure under `app/event-schemas/` should be:

```
app/event-schemas/
└── complete-data-draft/
    ├── 2025.06.04/
    │   └── complete-data-draft-schema.json
    └── 2025.07.01/
        └── complete-data-draft-schema.json
```

Use the [oncoanalyser-wgts-dna pipeline event schema stack](https://github.com/OrcaBus/service-oncoanalyser-wgts-dna-pipeline-manager) as the blueprint for this pattern.

> **Note**: Migrating from a flat schema file to the versioned directory structure may require redeployment of the stateful stack due to CloudFormation resource ID changes. Plan accordingly.

## Schema Registry

- Complete data draft event schemas must be registered with the `orcabus.data` event schema registry
- Use **JSON Schema version 2020-12** (`$schema: "https://json-schema.org/draft/2020-12/schema"`) for authoring
- The AWS Schemas registry technically supports only draft-4, but we author in 2020-12 and register as `JSONSchemaDraft4` type (the registry accepts it)

### CDK Registration Pattern

```typescript
new schemas.CfnSchema(scope, props.schemaName, {
  type: 'JSONSchemaDraft4',
  content: fs.readFileSync(schemaPath, 'utf-8'),
  registryName: DATA_SCHEMA_REGISTRY_NAME, // from platform-cdk-constructs
  schemaName: `${STACK_PREFIX}--${props.schemaName}`,
});
```

### SSM Parameter for Schema Lookup

Each schema should have a corresponding SSM parameter storing its registry coordinates:

```typescript
new ssm.StringParameter(scope, `${schemaName}-ssm-latest`, {
  parameterName: path.join(SSM_SCHEMA_ROOT, kebabCaseName, 'latest'),
  stringValue: JSON.stringify({
    registryName: schemaObj.registryName,
    schemaName: schemaObj.attrSchemaName,
    schemaVersion: schemaObj.attrSchemaVersion,
  }),
});
```

## Schema Validation Flow

Schema validation occurs in the `validateDraftDataAndPutReadyEvent` state machine:

1. **JSON Schema validation** — `validate_draft_complete_schema` Lambda validates against the registered schema
2. **Post-schema validation** — `post_schema_validation` Lambda performs business-rule checks that JSON Schema cannot express
3. On success → emit READY event
4. On failure → write comment to workflow run record, exit silently
