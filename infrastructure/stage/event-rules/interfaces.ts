import { EventPattern, IEventBus, Rule } from 'aws-cdk-lib/aws-events';

/**
 * EventBridge Rules Interfaces
 */
export type EventBridgeRuleNameList =
  | 'dragenWgtsDnaWrscReady'
  | 'dragenWgtsDnaIcav2WesAnalysisStateChange';

export const eventBridgeRuleNameList: EventBridgeRuleNameList[] = [
  'dragenWgtsDnaWrscReady',
  'dragenWgtsDnaIcav2WesAnalysisStateChange',
];

export interface EventBridgeRuleProps {
  ruleName: EventBridgeRuleNameList;
  eventBus: IEventBus;
  eventPattern: EventPattern;
}

export interface EventBridgeRulesProps {
  eventBus: IEventBus;
}

export interface EventBridgeRuleObject {
  ruleName: EventBridgeRuleNameList;
  ruleObject: Rule;
}

export type BuildIcav2AnalysisStateChangeRuleProps = Omit<EventBridgeRuleProps, 'eventPattern'>;
export type BuildDragenWgtsDnaReadyRuleProps = Omit<EventBridgeRuleProps, 'eventPattern'>;
