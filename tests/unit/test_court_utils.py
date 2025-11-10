from tracking import t
from reservations.queue.court_utils import normalize_court_sequence


def test_normalize_court_sequence_preserves_order():
    t('tests.unit.test_court_utils.test_normalize_court_sequence_preserves_order')
    raw = [2, 1, 2, '3', None, 'invalid', 1]
    result = normalize_court_sequence(raw)
    assert result == [2, 1, 3]


def test_normalize_court_sequence_respects_allowed():
    t('tests.unit.test_court_utils.test_normalize_court_sequence_respects_allowed')
    raw = [4, 1, 3]
    result = normalize_court_sequence(raw, allowed=[1, 2, 3])
    assert result == [1, 3]
