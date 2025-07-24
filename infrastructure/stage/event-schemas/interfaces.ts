// infrastructure/stage/event-schemas/interfaces.ts

export interface DecompressionStartedEvent {
  sampleId: string;
  fileName: string;
  timestamp: string;
}

export interface DecompressionCompletedEvent {
  sampleId: string;
  outputLocation: string;
  durationMs: number;
  timestamp: string;
}

export interface DecompressionFailedEvent {
  sampleId: string;
  errorMessage: string;
  errorCode?: string;
  timestamp: string;
}
