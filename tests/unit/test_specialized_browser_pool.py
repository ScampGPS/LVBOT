from tracking import t
from automation.browser.pools.specialized import SpecializedBrowserPool


class RecordingLogger:
    def __init__(self):
        t('tests.unit.test_specialized_browser_pool.RecordingLogger.__init__')
        self.records = []

    def info(self, message, *args):
        t('tests.unit.test_specialized_browser_pool.RecordingLogger.info')
        self.records.append(("info", message % args if args else message))

    def warning(self, message, *args):
        t('tests.unit.test_specialized_browser_pool.RecordingLogger.warning')
        self.records.append(("warning", message % args if args else message))


def _make_pool_with_logger():
    t('tests.unit.test_specialized_browser_pool._make_pool_with_logger')
    pool = object.__new__(SpecializedBrowserPool)
    pool.logger = RecordingLogger()
    return pool


def test_finalize_form_result_success_logs_and_returns():
    t('tests.unit.test_specialized_browser_pool.test_finalize_form_result_success_logs_and_returns')
    pool = _make_pool_with_logger()
    success, message = pool._finalise_form_result(1, "10:00", True, "Reserva confirmada")

    assert success is True
    assert message == "Successfully booked 10:00 - Reserva confirmada"
    assert ('info', 'Form submitted on court 1: Reserva confirmada') in pool.logger.records


def test_finalize_form_result_pending_confirmation():
    t('tests.unit.test_specialized_browser_pool.test_finalize_form_result_pending_confirmation')
    pool = _make_pool_with_logger()
    success, message = pool._finalise_form_result(2, "11:00", False, "No confirmation detected")

    assert success is True
    assert message == "Booking submitted (pending confirmation) - No confirmation detected"
    assert ('info', 'Booking submitted on court 2 (pending confirmation): No confirmation detected') in pool.logger.records


def test_finalize_form_result_failure_logs_warning():
    t('tests.unit.test_specialized_browser_pool.test_finalize_form_result_failure_logs_warning')
    pool = _make_pool_with_logger()
    success, message = pool._finalise_form_result(3, "12:00", False, "Validation error")

    assert success is False
    assert message == "Form error: Validation error"
    assert ('warning', 'Form submission failed on court 3: Validation error') in pool.logger.records
