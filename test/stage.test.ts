import { App, Aspects, Stack } from 'aws-cdk-lib';
import { Annotations, Match } from 'aws-cdk-lib/assertions';
import { SynthesisMessage } from 'aws-cdk-lib/cx-api';
import { AwsSolutionsChecks, NagSuppressions } from 'cdk-nag';
import { StatelessApplicationStack } from '../infrastructure/stage/stateless-application-stack';
import { getStatelessStackProps } from '../infrastructure/stage/config';

function synthesisMessageToString(sm: SynthesisMessage): string {
  return `${sm.entry.data} [${sm.id}]`;
}

describe('cdk-nag-stateless-toolchain-stack', () => {
  const app = new App({});

  // You should configure all stack (stateless, stateful) to be tested
  const applicationStack = new StatelessApplicationStack(
    app,
    'DeployStack',
    // Pick the prod environment to test as it is the most strict
    getStatelessStackProps('PROD')
  );

  Aspects.of(applicationStack).add(new AwsSolutionsChecks());
  applyNagSuppression(applicationStack);

  test(`cdk-nag AwsSolutions Pack errors`, () => {
    const errors = Annotations.fromStack(applicationStack)
      .findError('*', Match.stringLikeRegexp('AwsSolutions-.*'))
      .map(synthesisMessageToString);
    expect(errors).toHaveLength(0);
  });

  test(`cdk-nag AwsSolutions Pack warnings`, () => {
    const warnings = Annotations.fromStack(applicationStack)
      .findWarning('*', Match.stringLikeRegexp('AwsSolutions-.*'))
      .map(synthesisMessageToString);
    expect(warnings).toHaveLength(0);
  });
});

/**
 * apply nag suppression
 * @param stack
 */
function applyNagSuppression(stack: Stack) {
  NagSuppressions.addStackSuppressions(
    stack,
    [
      {
        id: 'AwsSolutions-S10',
        reason:
          'EventBridge schema registry backing bucket is AWS-managed and does not support enforcing SSL at the bucket policy level',
      },
    ],
    true
  );
  NagSuppressions.addStackSuppressions(
    stack,
    [
      {
        id: 'AwsSolutions-S1',
        reason:
          'EventBridge schema registry backing bucket is AWS-managed and does not support enabling access logging',
      },
    ],
    true
  );
}
