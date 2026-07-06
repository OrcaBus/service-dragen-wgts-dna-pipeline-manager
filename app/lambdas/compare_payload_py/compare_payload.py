#!/usr/bin/env python3

"""
Compare the payload of the original draft event and the newly constructed object.

We don't want to end up in an infinite loop, so we only emit a WRU event if the payload has actually changed.
"""

from deepdiff import DeepDiff


def handler(event, context):
    """
    Compare old and new payload using deep equality.

    Input:
    {
        "oldPayload": {...},
        "newPayload": {...}
    }

    Output:
    {
        "hasChanged": true/false
    }
    """
    old_payload = event['oldPayload']
    new_payload = event['newPayload']

    if not DeepDiff(old_payload, new_payload):
        return {"hasChanged": False}
    return {"hasChanged": True}
