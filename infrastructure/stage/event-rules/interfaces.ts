import { EventPattern, IEventBus, Rule } from 'aws-cdk-lib/aws-events';

/**
 * EventBridge Rules Interfaces
 */
export type EventBridgeRuleName =
  // Pre-draft
  | 'wrscDraftLegacy'
  | 'wrscDraft'
  // Pre-ready
  | 'wrscReadyLegacy'
  | 'wrscReady'
  // Post-submitted
  | 'icav2WesAnalysisStateChange';

export const eventBridgeRuleNameList: EventBridgeRuleName[] = [
  // Pre-draft
  'wrscDraftLegacy',
  'wrscDraft',
  // Pre-ready
  'wrscReadyLegacy',
  'wrscReady',
  // Post-submitted
  'icav2WesAnalysisStateChange',
];

export interface EventBridgeRuleProps {
  ruleName: EventBridgeRuleName;
  eventBus: IEventBus;
  eventPattern: EventPattern;
}

export interface EventBridgeRulesProps {
  eventBus: IEventBus;
}

export interface EventBridgeRuleObject {
  ruleName: EventBridgeRuleName;
  ruleObject: Rule;
}

export type BuildIcav2AnalysisStateChangeRuleProps = Omit<EventBridgeRuleProps, 'eventPattern'>;
export type BuildDragenWgtsDnaDraftRuleProps = Omit<EventBridgeRuleProps, 'eventPattern'>;
export type BuildDragenWgtsDnaReadyRuleProps = Omit<EventBridgeRuleProps, 'eventPattern'>;
