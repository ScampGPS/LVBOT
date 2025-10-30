"""Shared helpers for booking flow executions."""

from __future__ import annotations
from tracking import t

import logging
import time
from typing import Dict, Optional

from playwright.async_api import Page

from automation.executors.core import ExecutionResult
from datetime import datetime
from pathlib import Path


def safe_sleep(seconds: float) -> None:
    """Sleep helper that clamps to non-negative durations."""
    t('automation.executors.flows.helpers.safe_sleep')
    if seconds > 0:
        time.sleep(seconds)


_ARTIFACT_DIR = Path('logs/latest_log/booking_artifacts')


async def confirmation_result(
    page: Page,
    court_number: int,
    time_slot: str,
    user_info: Dict[str, str],
    *,
    logger: Optional[logging.Logger] = None,
    success_log: Optional[str] = None,
    failure_log: Optional[str] = None,
    failure_message: str = "Booking confirmation not detected",
    capture_on_failure: bool = True,
) -> ExecutionResult:
    """Build a booking execution result by inspecting page confirmation text."""
    t('automation.executors.flows.helpers.confirmation_result')

    # Wait for SPA content to load - check for key confirmation elements
    try:
        # Wait for confirmation text to appear (max 10 seconds)
        await page.wait_for_function(
            """() => {
                const text = document.body.textContent.toLowerCase();
                return text.includes('cita confirmada') ||
                       text.includes('reserva confirmada') ||
                       text.includes('confirmada') ||
                       text.includes('gracias por reservar');
            }""",
            timeout=10000
        )
        if logger:
            logger.info("Court %s: Confirmation text detected on page", court_number)
    except Exception as e:
        if logger:
            logger.debug("Court %s: Timeout waiting for confirmation text: %s", court_number, e)

    # Give extra time for all content to render
    await page.wait_for_timeout(2000)

    confirmation_text = await page.text_content("body")
    normalized = (confirmation_text or "").lower()

    success_tokens = (
        "cita confirmada",
        "reserva confirmada",
        "reserva completada",
        "reserva exitosa",
        "¡gracias por reservar",
        "gracias por reservar",
        "tu cita está confirmada",
    )

    if confirmation_text and any(token in normalized for token in success_tokens):
        if logger and success_log:
            logger.info(success_log, court_number)

        # Extract Google Calendar, Cancel/Modify, and ICS links from API
        google_calendar_link = None
        cancel_modify_link = None
        ics_calendar_link = None

        try:
            # Wait a bit more for React components to render (already waited 2s above)
            await page.wait_for_timeout(1000)

            # Extract appointment hash and owner key to call API
            api_data = await page.evaluate('''() => {
                const result = {
                    appointmentHash: null,
                    ownerKey: null,
                    currentUrl: window.location.href
                };

                // Extract owner key from BUSINESS global variable
                if (window.BUSINESS && window.BUSINESS.ownerKey) {
                    result.ownerKey = window.BUSINESS.ownerKey;
                }

                // Extract appointment hash from confirmation URL
                const urlMatch = window.location.href.match(/confirmation\/([a-f0-9]+)/);
                if (urlMatch) {
                    result.appointmentHash = urlMatch[1];
                }

                return result;
            }''')

            if logger:
                logger.debug("Court %s: API data extracted - ownerKey: %s, appointmentHash: %s",
                           court_number, api_data.get('ownerKey'), api_data.get('appointmentHash'))

            # Fetch appointment details from Acuity Scheduling API
            if api_data.get('appointmentHash') and api_data.get('ownerKey'):
                owner_key = api_data['ownerKey']
                appt_hash = api_data['appointmentHash']

                # Construct API URL (use the pretty URL domain from current page)
                current_url = api_data['currentUrl']
                if 'clublavilla.as.me' in current_url:
                    api_base = 'https://clublavilla.as.me'
                else:
                    api_base = 'https://app.acuityscheduling.com'

                api_url = f"{api_base}/api/scheduling/v1/appointments?owner={owner_key}&appointmentIds[]={appt_hash}"

                if logger:
                    logger.info("Court %s: Fetching appointment data from API: %s", court_number, api_url)

                # Make API request using Playwright's fetch
                try:
                    response = await page.request.get(api_url)

                    if response.ok:
                        appt_data = await response.json()

                        if logger:
                            logger.debug("Court %s: API response received with %d appointment(s)",
                                       court_number, len(appt_data.get('appointments', [])))

                        # Extract links from first appointment in response
                        appointments = appt_data.get('appointments', [])
                        if appointments:
                            appointment = appointments[0]

                            # Get Google Calendar link
                            google_calendar_link = appointment.get('addToGoogleLink')
                            if google_calendar_link and logger:
                                logger.info("Court %s: Extracted Google Calendar link from API", court_number)

                            # Get Cancel/Modify link
                            cancel_modify_link = appointment.get('confirmationPage')
                            if cancel_modify_link and logger:
                                logger.info("Court %s: Extracted cancel/modify link from API", court_number)

                            # Construct ICS/Outlook calendar link
                            # ICS link is typically the confirmationPage with &m=ics parameter
                            if cancel_modify_link:
                                ics_calendar_link = cancel_modify_link.replace('&action=appt', '&action=appt&m=ics')
                                if '&m=ics' not in ics_calendar_link:
                                    ics_calendar_link = f"{cancel_modify_link}&m=ics"
                                if logger:
                                    logger.info("Court %s: Constructed ICS/Outlook calendar link", court_number)
                    else:
                        if logger:
                            logger.warning("Court %s: API request failed with status %d", court_number, response.status)

                except Exception as api_err:
                    if logger:
                        logger.warning("Court %s: Failed to fetch from API: %s", court_number, api_err)
            else:
                if logger:
                    logger.warning("Court %s: Could not extract appointment hash or owner key from page", court_number)

        except Exception as e:
            if logger:
                logger.warning("Court %s: Failed to extract confirmation links: %s", court_number, e)

        # Log final link extraction results
        if logger:
            links_found = []
            if google_calendar_link:
                links_found.append("Google Calendar")
            if cancel_modify_link:
                links_found.append("cancel/modify")
            if ics_calendar_link:
                links_found.append("ICS/Outlook")

            if len(links_found) == 3:
                logger.info("Court %s: Successfully extracted all confirmation links (Google, Cancel/Modify, ICS)", court_number)
            elif links_found:
                logger.warning("Court %s: Extracted only %s link(s)", court_number, ", ".join(links_found))
            else:
                logger.warning("Court %s: No confirmation links extracted", court_number)

        return ExecutionResult(
            success=True,
            court_number=court_number,
            court_reserved=court_number,
            time_reserved=time_slot,
            user_name=user_info.get("first_name"),
            google_calendar_link=google_calendar_link,
            cancel_modify_link=cancel_modify_link,
            ics_calendar_link=ics_calendar_link,
        )

    irregular_tokens = (
        "uso irregular",
        "irregular del sitio",
        "detectó un uso irregular",
    )
    if confirmation_text and any(token in normalized for token in irregular_tokens):
        message = "Irregular usage warning encountered"
        if logger:
            logger.warning("Court %s triggered irregular usage warning", court_number)
        return ExecutionResult(
            success=False,
            error_message=message,
            court_number=court_number,
        )

    if logger and failure_log:
        logger.warning(failure_log, court_number)

    if capture_on_failure:
        await _capture_failure_artifacts(
            page,
            court_number=court_number,
            time_slot=time_slot,
            logger=logger,
        )

    return ExecutionResult(
        success=False,
        error_message=failure_message,
        court_number=court_number,
    )


async def _capture_failure_artifacts(
    page: Page,
    *,
    court_number: int,
    time_slot: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Persist a screenshot and HTML snapshot when confirmation detection fails."""

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    slot_label = time_slot.replace(":", "-") or "unspecified"

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    screenshot_path = _ARTIFACT_DIR / f"court{court_number}_{slot_label}_{timestamp}.png"
    html_path = _ARTIFACT_DIR / f"court{court_number}_{slot_label}_{timestamp}.html"

    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception as exc:  # pragma: no cover - best effort logging
        if logger:
            logger.debug("Failed to capture screenshot: %s", exc)

    try:
        html_content = await page.content()
        html_path.write_text(html_content or "", encoding="utf-8")
    except Exception as exc:  # pragma: no cover - best effort logging
        if logger:
            logger.debug("Failed to write HTML artifact: %s", exc)

    if logger:
        logger.warning(
            "Stored booking artifacts for court %s slot %s at %s",
            court_number,
            time_slot,
            screenshot_path,
        )


__all__ = ["safe_sleep", "confirmation_result"]
