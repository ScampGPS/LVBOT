import asyncio
from datetime import datetime

import pytest

from monitoring.availability_poller import AvailabilityPoller
import logging


class StubFetcher:
    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.index = 0

    async def fetch(self):
        snapshot = self.snapshots[min(self.index, len(self.snapshots) - 1)]
        self.index += 1
        await asyncio.sleep(0)
        return snapshot


@pytest.mark.asyncio
async def test_availability_poller_detects_added_and_removed_slots():
    fetcher = StubFetcher([
        {1: {'2025-01-01': ['09:00']}},
        {1: {'2025-01-01': ['09:00', '10:00']}},
    ])

    poller = AvailabilityPoller(fetcher.fetch, logger=logging.getLogger('test_poller'))

    first = await poller.poll()
    assert first.changes == {}

    second = await poller.poll()
    assert 1 in second.changes
    change = second.changes[1]
    assert change.added['2025-01-01'] == ['10:00']
    assert change.removed == {}

@pytest.mark.asyncio
async def test_availability_poller_handles_errors():
    fetcher = StubFetcher([
        {1: {'error': 'failed'}},
        {1: {'2025-01-01': ['09:00']}},
    ])

    poller = AvailabilityPoller(fetcher.fetch, logger=logging.getLogger('test_poller'))

    first = await poller.poll()
    assert first.changes[1].error == 'failed'

    second = await poller.poll()
    assert second.changes[1].error == 'Recovered from error'
