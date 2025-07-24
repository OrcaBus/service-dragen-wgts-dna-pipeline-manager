// scripts/publishSchemas.ts

import { publishSchemas } from "@orcabus/event-schema-registry";
import {
  decompressionStarted,
  decompressionCompleted,
  decompressionFailed
} from "../infrastructure/stage/event-schemas";

async function main() {
  await publishSchemas([
    decompressionStarted,
    decompressionCompleted,
    decompressionFailed
  ]);
  console.log("✅ Event schemas published successfully");
}

main().catch(err => {
  console.error("❌ Failed to publish schemas", err);
  process.exit(1);
});
