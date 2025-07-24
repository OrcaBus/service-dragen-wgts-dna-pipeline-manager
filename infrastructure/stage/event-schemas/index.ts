// infrastructure/stage/event-schemas/index.ts

import { EventSchema } from "@orcabus/event-schema-registry"; // Adjust this import to match your actual schema lib
import {
  DecompressionStartedEvent,
  DecompressionCompletedEvent,
  DecompressionFailedEvent
} from "./interfaces";

export const decompressionStarted: EventSchema<DecompressionStartedEvent> = {
  name: "decompression.started",
  version: 1,
  schema: {
    type: "object",
    required: ["sampleId", "fileName", "timestamp"],
    properties: {
      sampleId: { type: "string" },
      fileName: { type: "string" },
      timestamp: { type: "string", format: "date-time" }
    }
  }
};

export const decompressionCompleted: EventSchema<DecompressionCompletedEvent> = {
  name: "decompression.completed",
  version: 1,
  schema: {
    type: "object",
    required: ["sampleId", "outputLocation", "durationMs", "timestamp"],
    properties: {
      sampleId: { type: "string" },
      outputLocation: { type: "string" },
      durationMs: { type: "number" },
      timestamp: { type: "string", format: "date-time" }
    }
  }
};

export const decompressionFailed: EventSchema<DecompressionFailedEvent> = {
  name: "decompression.failed",
  version: 1,
  schema: {
    type: "object",
    required: ["sampleId", "errorMessage", "timestamp"],
    properties: {
      sampleId: { type: "string" },
      errorMessage: { type: "string" },
      errorCode: { type: "string" },
      timestamp: { type: "string", format: "date-time" }
    }
  }
};
