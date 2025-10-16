"""
Unified Court Monitor - Monitors court availability with flexible strategies.
"""
from utils.tracking import t

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
from playwright.async_api import async_playwright, Page, Frame

class CourtMonitor:
    """A unified court monitor with configurable strategies."""

    def __init__(self, headless: bool = True, debug: bool = False):
        t('monitoring.court_monitor.CourtMonitor.__init__')
        self.timezone = pytz.timezone('America/Guatemala')
        self.base_url = "https://www.clublavilla.com/haz-tu-reserva"
        self.headless = headless
        self.debug = debug
        self.logger = logging.getLogger('CourtMonitor')
        self._setup_logging(logging.DEBUG if debug else logging.INFO)

        from infrastructure.constants import WEEKDAY_COURT_HOURS, WEEKEND_COURT_HOURS
        self.weekday_slots = WEEKDAY_COURT_HOURS
        self.weekend_slots = WEEKEND_COURT_HOURS

    def _setup_logging(self, level):
        t('monitoring.court_monitor.CourtMonitor._setup_logging')
        log_file = f'court_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        logging.basicConfig(
            level=level,
            format='%(asctime)s.%(msecs)03d - [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def get_slots_for_date(self, date: datetime) -> List[str]:
        """Get available slots for a specific date."""
        t('monitoring.court_monitor.CourtMonitor.get_slots_for_date')
        return self.weekend_slots if date.weekday() >= 5 else self.weekday_slots

    async def monitor_all_day(self, court_numbers: List[int], advance_seconds: int = 30):
        """Monitor specified courts continuously for slots 48 hours in advance."""
        t('monitoring.court_monitor.CourtMonitor.monitor_all_day')
        self.logger.info(f"48-HOUR ADVANCE COURT MONITORING STARTED for courts: {court_numbers}")
        while True:
            now = datetime.now(self.timezone)
            target_playing_date = now + timedelta(hours=48)
            available_slots = self.get_slots_for_date(target_playing_date)
            next_slot_to_monitor = None

            for slot_time in available_slots:
                hour, minute = map(int, slot_time.split(':'))
                playing_datetime = target_playing_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                booking_opens_at = playing_datetime - timedelta(hours=48)
                monitor_start_time = booking_opens_at - timedelta(seconds=advance_seconds)

                if monitor_start_time > now:
                    next_slot_to_monitor = (slot_time, playing_datetime, monitor_start_time)
                    break
            
            if next_slot_to_monitor:
                slot_time, playing_datetime, monitor_start_time = next_slot_to_monitor
                wait_seconds = (monitor_start_time - now).total_seconds()
                self.logger.info(f"Next slot to book: {slot_time} on {playing_datetime.date()}. Waiting {wait_seconds:.0f} seconds.")
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)

                for court_number in court_numbers:
                    self.logger.info(f"Monitoring Court {court_number} for playing time: {playing_datetime.strftime('%Y-%m-%d %H:%M')}")
                    await self.monitor_single_slot(court_number, slot_time, advance_seconds=advance_seconds)
            else:
                self.logger.info("No more slots to monitor in this hour, waiting 30 minutes...")
                await asyncio.sleep(1800)

    async def monitor_single_slot(self, court_number: int, slot_time: str, advance_seconds: int = 30, duration_seconds: int = 90) -> Dict:
        """Monitor a single court/time slot combination."""
        t('monitoring.court_monitor.CourtMonitor.monitor_single_slot')
        self.logger.info(f"MONITORING: Court {court_number} - Slot {slot_time}")
        slot_found = asyncio.Event()
        winning_browser = None

        now = datetime.now(self.timezone)
        hour, minute = map(int, slot_time.split(':'))
        expected_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if expected_time <= now:
            expected_time += timedelta(days=1)

        start_time = expected_time - timedelta(seconds=advance_seconds)
        end_time = expected_time + timedelta(seconds=duration_seconds)

        await self._wait_until_start(start_time)

        browser_configs = [
            ("Browser1-Wait", "wait", 0),
            ("Browser2-Refresh", "refresh", 0),
            ("Browser3-Refresh", "refresh", 1),
            ("Browser4-SmartRefresh", "back", 2),
            ("Browser5-SmartRefresh", "back", 3),
        ]

        async with async_playwright() as playwright:
            tasks = []
            for name, strategy, delay in browser_configs:
                task = asyncio.create_task(self._monitor_with_browser(
                    playwright, name, strategy, delay, court_number, slot_time, expected_time, end_time, slot_found, winning_browser
                ))
                tasks.append(task)
            
            browser_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process and log results
        # ... (result processing logic from original files)
        return {}

    async def _wait_until_start(self, start_time: datetime):
        """Wait until monitoring should start."""
        t('monitoring.court_monitor.CourtMonitor._wait_until_start')
        now = datetime.now(self.timezone)
        if now < start_time:
            wait_seconds = (start_time - now).total_seconds()
            self.logger.info(f"Waiting for {wait_seconds:.0f} seconds...")
            await asyncio.sleep(wait_seconds)

    async def _monitor_with_browser(
        self,
        playwright,
        browser_name: str,
        strategy: str,
        start_delay: int,
        court_number: int,
        slot_time: str,
        expected_time: datetime,
        end_time: datetime,
        slot_found: asyncio.Event,
        winning_browser
    ) -> Dict:
        """Monitor with a single browser using specified strategy"""
        t('monitoring.court_monitor.CourtMonitor._monitor_with_browser')
        
        logger = logging.getLogger(browser_name)
        result = {
            'browser': browser_name,
            'strategy': strategy,
            'checks': 0,
            'iframe_found_at': None,
            'button_found_at': None,
            'errors': []
        }
        
        if start_delay > 0:
            await asyncio.sleep(start_delay)
        
        browser = None
        try:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='es-ES',
                timezone_id='America/Guatemala'
            )
            page = await context.new_page()
            
            if strategy == "wait":
                await self._wait_strategy(page, court_number, slot_time, expected_time, end_time, logger, result, slot_found)
            elif strategy == "refresh":
                await self._refresh_strategy(page, court_number, slot_time, expected_time, end_time, logger, result, slot_found)
            else:  # strategy == "back"
                await self._back_strategy(page, court_number, slot_time, expected_time, end_time, logger, result, slot_found)
                
        except Exception as e:
            logger.error(f"Browser error: {e}")
            result['errors'].append(str(e))
        finally:
            if browser:
                await browser.close()
        
        return result

    async def _wait_strategy(self, page: Page, court_number: int, slot_time: str, 
                           expected_time: datetime, end_time: datetime, logger, result: Dict, slot_found: asyncio.Event):
        """Wait strategy: Load once and monitor for changes"""
        t('monitoring.court_monitor.CourtMonitor._wait_strategy')
        logger.info("Using WAIT strategy")
        await page.goto(self.base_url, wait_until='domcontentloaded')
        frame = await self._setup_booking_page(page, court_number, logger)
        if not frame: return

        result['iframe_found_at'] = datetime.now(self.timezone).isoformat()
        while datetime.now(self.timezone) < end_time and not slot_found.is_set():
            result['checks'] += 1
            hour_button = await self._find_hour_button(frame, slot_time)
            if hour_button and hour_button['enabled']:
                result['button_found_at'] = datetime.now(self.timezone).isoformat()
                logger.info(f"*** SLOT FOUND! ***")
                slot_found.set()
                break
            await asyncio.sleep(1)

    async def _refresh_strategy(self, page: Page, court_number: int, slot_time: str,
                              expected_time: datetime, end_time: datetime, logger, result: Dict, slot_found: asyncio.Event):
        """Refresh strategy: Reload page periodically"""
        t('monitoring.court_monitor.CourtMonitor._refresh_strategy')
        logger.info("Using REFRESH strategy")
        while datetime.now(self.timezone) < end_time and not slot_found.is_set():
            result['checks'] += 1
            try:
                await page.goto(self.base_url, wait_until='domcontentloaded')
                frame = await self._setup_booking_page(page, court_number, logger)
                if frame:
                    if not result['iframe_found_at']:
                        result['iframe_found_at'] = datetime.now(self.timezone).isoformat()
                    hour_button = await self._find_hour_button(frame, slot_time)
                    if hour_button and hour_button['enabled']:
                        result['button_found_at'] = datetime.now(self.timezone).isoformat()
                        logger.info(f"*** SLOT FOUND! ***")
                        slot_found.set()
                        break
            except Exception as e:
                logger.debug(f"Refresh error: {e}")
            if not slot_found.is_set():
                await asyncio.sleep(5)

    async def _back_strategy(self, page: Page, court_number: int, slot_time: str,
                           expected_time: datetime, end_time: datetime, logger, result: Dict, slot_found: asyncio.Event):
        """Smart refresh strategy: Refresh only when times visible but target not found"""
        t('monitoring.court_monitor.CourtMonitor._back_strategy')
        logger.info("Using SMART REFRESH strategy")
        await page.goto(self.base_url, wait_until='domcontentloaded')
        frame = await self._setup_booking_page(page, court_number, logger)
        if not frame: return

        while datetime.now(self.timezone) < end_time and not slot_found.is_set():
            result['checks'] += 1
            try:
                all_hours = await self._get_all_visible_hours(frame)
                if all_hours:
                    if slot_time not in all_hours:
                        logger.info(f"Times visible but {slot_time} not found - refreshing page")
                        await page.goto(self.base_url, wait_until='domcontentloaded')
                        frame = await self._setup_booking_page(page, court_number, logger)
                        if not frame: continue
                
                hour_button = await self._find_hour_button(frame, slot_time)
                if hour_button and hour_button['enabled']:
                    result['button_found_at'] = datetime.now(self.timezone).isoformat()
                    logger.info(f"*** SLOT FOUND! ***")
                    slot_found.set()
                    break
            except Exception as e:
                logger.debug(f"Back strategy error: {e}")
            if not slot_found.is_set():
                await asyncio.sleep(1)

    async def _setup_booking_page(self, page: Page, court_number: int, logger) -> Optional[Frame]:
        """Setup booking page by clicking RESERVAR button"""
        t('monitoring.court_monitor.CourtMonitor._setup_booking_page')
        try:
            iframe_elem = await page.wait_for_selector('iframe', timeout=5000)
            frame = await iframe_elem.content_frame()
            if not frame: return None
            await frame.wait_for_load_state('domcontentloaded')
            reserve_buttons = await frame.query_selector_all('button:has-text("Reservar")')
            if len(reserve_buttons) >= court_number:
                await reserve_buttons[court_number - 1].click()
                await page.wait_for_timeout(2000)
                return frame
            return None
        except Exception as e:
            logger.debug(f"Setup error: {e}")
            return None

    async def _get_all_visible_hours(self, frame: Frame) -> List[str]:
        """Get all visible hour buttons"""
        t('monitoring.court_monitor.CourtMonitor._get_all_visible_hours')
        visible_hours = []
        try:
            time_elements = await frame.query_selector_all('*:has-text(":")')
            for elem in time_elements:
                try:
                    text = await elem.text_content()
                    if text and ':' in text and len(text.strip()) <= 10 and await elem.is_visible():
                        import re
                        time_match = re.search(r'\d{1,2}:\d{2}', text)
                        if time_match:
                            visible_hours.append(time_match.group())
                except:
                    pass
            return list(set(visible_hours))
        except:
            return []

    async def _find_hour_button(self, frame: Frame, slot_time: str) -> Optional[Dict]:
        """Find the hour button for the specified time slot"""
        t('monitoring.court_monitor.CourtMonitor._find_hour_button')
        try:
            time_elements = await frame.query_selector_all(f'*:has-text("{slot_time}")')
            for elem in time_elements:
                try:
                    text = await elem.text_content()
                    if text and slot_time == text.strip():
                        tag = await elem.evaluate("el => el.tagName")
                        if await elem.is_visible() and (tag in ['BUTTON', 'A'] or await elem.evaluate("el => window.getComputedStyle(el).cursor === 'pointer'")):
                            return {'element': elem, 'enabled': await elem.is_enabled()}
                except:
                    pass
            return None
        except:
            return None

    async def explore_booking_flow(self, court_number: int = 1):
        """Explore the booking flow step by step for debugging."""
        t('monitoring.court_monitor.CourtMonitor.explore_booking_flow')
        self.logger.info(f"Starting booking flow exploration for Court {court_number}...")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False, slow_mo=1000)
            page = await browser.new_page()
            try:
                await page.goto(self.base_url, wait_until='domcontentloaded')
                frame = await self._setup_booking_page(page, court_number, self.logger)
                if not frame: return

                self.logger.info("Reading available days and times...")
                # ... (Add logic to read days and times)

                self.logger.info("Looking for hour buttons...")
                hour_buttons = await self._find_hour_buttons(frame)
                if hour_buttons:
                    self.logger.info(f"Found {len(hour_buttons)} hour buttons!")
                    await hour_buttons[0]['element'].click()
                    await page.wait_for_timeout(3000)

                    self.logger.info("Looking for info form...")
                    # ... (Add logic to check for form)
                else:
                    self.logger.info("No hour buttons found.")
                
                self.logger.info("Keeping browser open for 60 seconds for manual exploration...")
                await page.wait_for_timeout(60000)

            finally:
                await browser.close()
