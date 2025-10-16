"""
Acuity booking form handler for filling appointment details
Following LVBOT principles: modular, reusable, focused on one task
Simplified implementation using working patterns from successful tests
"""
from utils.tracking import t

import asyncio
import logging
import time
from typing import Dict, Tuple
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class AcuityBookingForm:
    """Handles the Acuity appointment booking form interaction using simple, reliable methods"""
    
    # Form field selectors for direct URL booking form
    FORM_SELECTORS = {
        'client.firstName': 'input[name="client.firstName"]',
        'client.lastName': 'input[name="client.lastName"]', 
        'client.phone': 'input[name="client.phone"]',
        'client.email': 'input[name="client.email"]'
    }
    
    def __init__(self, use_javascript=True):
        """
        Initialize the booking form handler
        
        Args:
            use_javascript (bool): If True, use JavaScript form filling. If False, use native Playwright methods.
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm.__init__')
        self.logger = logger
        self.use_javascript = use_javascript
        
    async def check_form_validation_errors(self, page: Page) -> Tuple[bool, list]:
        """
        Check if form has validation errors that would prevent submission
        
        Returns:
            Tuple of (has_errors: bool, error_messages: list)
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm.check_form_validation_errors')
        try:
            validation_result = await page.evaluate("""
            () => {
                const errors = [];
                
                // Check for red text validation messages (Spanish)
                const redTextElements = Array.from(document.querySelectorAll('*')).filter(el => {
                    const style = window.getComputedStyle(el);
                    const text = el.textContent.trim();
                    return (style.color.includes('red') || 
                           style.color === 'rgb(255, 0, 0)' ||
                           style.color === 'rgba(255, 0, 0, 1)') && 
                           text.includes('obligatorio');
                });
                
                redTextElements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text && !errors.includes(text)) {
                        errors.push(text);
                    }
                });
                
                // Check for empty required fields
                const requiredFields = document.querySelectorAll('input[name*="client"]');
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        errors.push(`${field.name} is empty`);
                    }
                });
                
                return {
                    hasErrors: errors.length > 0,
                    errors: errors
                };
            }
            """)
            
            has_errors = validation_result.get('hasErrors', True)
            errors = validation_result.get('errors', [])
            
            if has_errors:
                self.logger.warning("⚠️ Form validation errors detected:")
                for error in errors:
                    self.logger.warning(f"   • {error}")
            else:
                self.logger.info("✅ No form validation errors found")
            
            return has_errors, errors
            
        except Exception as e:
            self.logger.error(f"❌ Error checking form validation: {e}")
            return True, [f"Error checking validation: {str(e)}"]

    async def fill_booking_form(
        self, 
        page: Page,
        user_data: Dict[str, str],
        wait_for_navigation: bool = True
    ) -> Tuple[bool, str]:
        """
        Fill out the Acuity booking form with user data using simple, reliable approach
        
        Args:
            page: The Playwright page object
            user_data: Dictionary containing:
                - client.firstName: First name
                - client.lastName: Last name  
                - client.phone: Phone number
                - client.email: Email address
            wait_for_navigation: Whether to wait for page navigation after submit
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm.fill_booking_form')
        try:
            # Validate required fields
            required_fields = ['client.firstName', 'client.lastName', 'client.phone', 'client.email']
            missing_fields = [field for field in required_fields if field not in user_data or not user_data[field]]
            
            if missing_fields:
                self.logger.error(f"❌ Missing required fields: {', '.join(missing_fields)}")
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            
            # Enable trace recording for debugging (in test environments)
            context = page.context
            trace_enabled = False
            try:
                # Start tracing for form filling debugging
                await context.tracing.start(screenshots=True, snapshots=True, sources=True)
                trace_enabled = True
                self.logger.info("🎥 Started trace recording for form filling debugging")
            except Exception as trace_error:
                self.logger.warning(f"⚠️ Could not start tracing: {trace_error}")

            try:
                if self.use_javascript:
                    self.logger.info("🔍 Starting JavaScript form filling approach")
                    filled_count = await self._fill_form_javascript(page, user_data)
                else:
                    self.logger.info("🔍 Starting native Playwright form filling approach")
                    filled_count = await self._fill_form_playwright(page, user_data)
            finally:
                # Stop and save trace
                if trace_enabled:
                    try:
                        trace_path = f"/mnt/c/Documents/code/python/LVBot/debugging/form_fill_trace_{int(time.time())}.zip"
                        await context.tracing.stop(path=trace_path)
                        self.logger.info(f"💾 Saved form filling trace to: {trace_path}")
                    except Exception as trace_error:
                        self.logger.warning(f"⚠️ Could not save trace: {trace_error}")
                
            if filled_count == 0:
                return False, "❌ Could not fill any form fields"
            
            self.logger.info(f"✅ Filled {filled_count} fields successfully")
            
            # Wait for form validation to process
            await asyncio.sleep(2)
            
            # Check for validation errors before submission
            has_errors, errors = await self.check_form_validation_errors(page)
            
            if has_errors:
                self.logger.error("❌ Form has validation errors, cannot submit:")
                for error in errors:
                    self.logger.error(f"   • {error}")
                return False, f"Form validation failed: {'; '.join(errors)}"
            
            # Submit form using JavaScript button click
            self.logger.info("🚀 Submitting form...")
            submit_success = await self._submit_form_simple(page)
            
            if submit_success:
                # Check for booking success and errors
                success, message = await self.check_booking_success(page)
                if not success and 'bot_detected' in message:
                    self.logger.warning("🚫 Bot detection triggered - sistema bloqueó uso automatizado")
                    return False, "❌ Sistema detectó bot - usar navegador manual para reservar"
                elif not success and 'validation_error' in message:
                    self.logger.warning(f"⚠️ Form validation errors: {message}")
                    return False, message
                else:
                    return success, message
            else:
                return False, "❌ Form submission failed"
            
        except Exception as e:
            self.logger.error(f"❌ Error in form filling: {e}")
            return False, f"Error in form filling: {e}"

    async def _fill_form_javascript(self, page: Page, user_data: Dict[str, str]) -> int:
        """
        Fill form using JavaScript approach
        
        Returns:
            int: Number of fields successfully filled
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm._fill_form_javascript')
        self.logger.info("📝 Filling form fields with JavaScript...")
        
        result = await page.evaluate("""
        (userData) => {
            const fields = {
                'client.firstName': userData['client.firstName'],
                'client.lastName': userData['client.lastName'], 
                'client.email': userData['client.email'],
                'client.phone': userData['client.phone']
            };
            
            let filled = 0;
            const results = [];
            
            Object.entries(fields).forEach(([fieldName, value]) => {
                if (!value) return;
                
                const element = document.querySelector(`input[name="${fieldName}"]`);
                if (element) {
                    element.value = value;
                    // Trigger events for validation
                    element.dispatchEvent(new Event('input', {bubbles: true}));
                    element.dispatchEvent(new Event('change', {bubbles: true}));
                    filled++;
                    results.push(`✅ ${fieldName}: ${value}`);
                } else {
                    results.push(`❌ ${fieldName}: field not found`);
                }
            });
            
            return {filled: filled, results: results};
        }
        """, user_data)
        
        filled_count = result.get('filled', 0)
        for log_msg in result.get('results', []):
            self.logger.info(f"  {log_msg}")
            
        return filled_count

    async def _fill_form_playwright(self, page: Page, user_data: Dict[str, str]) -> int:
        """
        Fill form using enhanced Playwright methods with debugging
        
        Returns:
            int: Number of fields successfully filled
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm._fill_form_playwright')
        self.logger.info("📝 Filling form fields with enhanced Playwright approach...")
        
        fields = [
            ('client.firstName', user_data.get('client.firstName', '')),
            ('client.lastName', user_data.get('client.lastName', '')),
            ('client.phone', user_data.get('client.phone', '')),
            ('client.email', user_data.get('client.email', ''))
        ]
        
        filled_count = 0
        
        # Enhanced pre-fill diagnostics
        self.logger.info("🔍 Running pre-fill diagnostics...")
        try:
            # Check if any form fields are present
            all_fields = await page.query_selector_all('input[name*="client."]')
            self.logger.info(f"📊 Found {len(all_fields)} client form fields")
            
            # Check for JavaScript errors
            js_ready = await page.evaluate('() => document.readyState')
            self.logger.info(f"📊 Document ready state: {js_ready}")
            
            # Wait for potential form initialization
            await page.wait_for_timeout(1000)
            
        except Exception as diag_error:
            self.logger.warning(f"⚠️ Diagnostics failed: {diag_error}")
        
        for field_name, value in fields:
            if not value:
                continue
                
            try:
                selector = f'input[name="{field_name}"]'
                locator = page.locator(selector)
                
                # Enhanced actionability checks
                self.logger.info(f"🔍 Checking actionability for {field_name}...")
                
                # Wait for element to be visible and enabled
                await locator.wait_for(state='visible', timeout=10000)
                await locator.wait_for(state='attached', timeout=5000)
                
                # Check element state
                is_visible = await locator.is_visible()
                is_enabled = await locator.is_enabled()
                count = await locator.count()
                
                self.logger.info(f"📊 {field_name} - Visible: {is_visible}, Enabled: {is_enabled}, Count: {count}")
                
                if not is_visible or not is_enabled or count == 0:
                    self.logger.warning(f"⚠️ {field_name} not ready - trying JavaScript fallback")
                    # JavaScript injection fallback
                    await page.evaluate(f'''
                        (value) => {{
                            const field = document.querySelector('input[name="{field_name}"]');
                            if (field) {{
                                field.value = value;
                                field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                    ''', value)
                    filled_count += 1
                    self.logger.info(f"  ✅ {field_name}: {value} (JavaScript fallback)")
                    continue
                
                # Try native Playwright approach with timeout
                self.logger.info(f"🎯 Filling {field_name} with native Playwright...")
                
                # Click to focus with timeout
                await locator.click(timeout=5000)
                await page.wait_for_timeout(200)
                
                # Clear and fill with timeout
                await locator.fill(value, timeout=5000)
                await page.wait_for_timeout(200)
                
                # Tab out to trigger validation
                await locator.press('Tab', timeout=3000)
                await page.wait_for_timeout(200)
                
                filled_count += 1
                self.logger.info(f"  ✅ {field_name}: {value} (native Playwright)")
                
            except Exception as e:
                self.logger.error(f"  ❌ {field_name}: {str(e)}")
        
        return filled_count

    async def fill_form(self, page: Page, user_info: Dict[str, str]) -> bool:
        """
        Convenience method for external use - fills form without submission
        
        Args:
            page: Playwright page object
            user_info: Dictionary with user information
            
        Returns:
            bool: True if form filled successfully
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm.fill_form')
        try:
            # Map external keys to internal format
            user_data = {
                'client.firstName': user_info.get('first_name', ''),
                'client.lastName': user_info.get('last_name', ''),
                'client.phone': user_info.get('phone', ''),
                'client.email': user_info.get('email', '')
            }
            
            # Use same filling logic
            fields = [
                ('input[name="client.firstName"]', user_data['client.firstName']),
                ('input[name="client.lastName"]', user_data['client.lastName']),
                ('input[name="client.phone"]', user_data['client.phone']),
                ('input[name="client.email"]', user_data['client.email'])
            ]
            
            filled_count = 0
            
            for selector, value in fields:
                if not value:
                    continue
                    
                try:
                    # Clear existing value and type new value
                    await page.fill(selector, "")
                    await page.wait_for_timeout(300)
                    await page.type(selector, value)
                    await page.wait_for_timeout(300)
                    
                    # Trigger blur to activate validation
                    await page.evaluate(f'document.querySelector(\'{selector}\').blur()')
                    await page.wait_for_timeout(300)
                    
                    filled_count += 1
                    self.logger.info(f"  ✅ {selector}: {value}")
                    
                except Exception as e:
                    self.logger.error(f"  ❌ {selector}: {str(e)}")
            
            # Wait for validation to process
            await asyncio.sleep(2)
            
            # Check validation
            has_errors, errors = await self.check_form_validation_errors(page)
            
            if has_errors:
                self.logger.error("❌ Form validation failed after filling")
                return False
            
            self.logger.info(f"✅ Successfully filled {filled_count}/4 fields")
            return filled_count > 0
            
        except Exception as e:
            self.logger.error(f"❌ Error in fill_form: {e}")
            return False


    async def _submit_form_simple(self, page: Page) -> bool:
        """
        Submit form using simple JavaScript button click
        
        Returns:
            bool: True if form was submitted successfully
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm._submit_form_simple')
        try:
            self.logger.info("🚀 Submitting form with JavaScript...")
            
            # Use JavaScript to find and click submit button
            result = await page.evaluate("""
            () => {
                // Find button containing "Confirmar" text
                const buttons = Array.from(document.querySelectorAll('button'));
                const confirmButton = buttons.find(btn => 
                    btn.textContent.includes('Confirmar') && 
                    btn.offsetParent !== null
                );
                
                if (confirmButton) {
                    confirmButton.click();
                    return {success: true, buttonText: confirmButton.textContent.trim()};
                }
                
                // Fallback to any submit button
                const submitButton = document.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.click();
                    return {success: true, buttonText: 'submit button'};
                }
                
                return {success: false, error: 'No submit button found'};
            }
            """)
            
            if result.get('success'):
                self.logger.info(f"✅ Form submitted using: {result.get('buttonText')}")
                await asyncio.sleep(2)  # Wait for submission to process
                return True
            else:
                self.logger.error(f"❌ Could not submit form: {result.get('error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error submitting form: {e}")
            return False

    async def check_booking_success(self, page: Page) -> Tuple[bool, str]:
        """
        Check if the booking was successful after form submission
        
        Args:
            page: Playwright page after form submission
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        t('automation.forms.acuity_booking_form.AcuityBookingForm.check_booking_success')
        try:
            self.logger.info("🔍 Checking booking success...")
            
            # Wait for page to update
            await asyncio.sleep(2)
            
            # Use JavaScript to check for success indicators and errors
            result = await page.evaluate("""
            () => {
                const url = window.location.href;
                const text = document.body.innerText || '';
                const textLower = text.toLowerCase();
                
                // Check for bot detection error first
                if (text.includes('Se detectó un uso irregular del sitio') || 
                    text.includes('uso irregular') ||
                    text.includes('Comunícate con el negocio')) {
                    return {
                        success: false,
                        error: 'bot_detected',
                        message: 'Sistema detectó uso automatizado - contactar negocio para reservar'
                    };
                }
                
                // Check for form validation errors
                const errorElements = document.querySelectorAll('.error, .field-error, [class*="error"]');
                if (errorElements.length > 0) {
                    const errors = Array.from(errorElements).map(el => el.textContent.trim()).filter(t => t);
                    if (errors.length > 0) {
                        return {
                            success: false,
                            error: 'validation_error',
                            message: `Errores de validación: ${errors.join(', ')}`
                        };
                    }
                }
                
                // Check for confirmation URL pattern
                const confirmMatch = url.match(/\\/confirmation\\/([a-zA-Z0-9]+)/);
                if (confirmMatch) {
                    const confirmationId = confirmMatch[1];
                    // Look for user name
                    const nameMatch = text.match(/([A-Za-z]+),\\s*¡Tu cita está confirmada!/);
                    return {
                        success: true,
                        type: 'confirmation',
                        confirmationId: confirmationId,
                        userName: nameMatch ? nameMatch[1] : null
                    };
                }
                
                // Check for success text
                const successWords = ['confirmación', 'confirmada', 'exitoso', 'gracias'];
                for (const word of successWords) {
                    if (textLower.includes(word)) {
                        return {success: true, type: 'success_text', indicator: word};
                    }
                }
                
                // Check for error text
                const errorWords = ['error', 'problema', 'no disponible'];
                for (const word of errorWords) {
                    if (textLower.includes(word)) {
                        return {success: false, type: 'error_text', indicator: word};
                    }
                }
                
                return {success: null, type: 'unclear', text: text.substring(0, 200)};
            }
            """)
            
            if result.get('success') is True:
                if result.get('type') == 'confirmation':
                    confirmation_id = result.get('confirmationId', '')
                    user_name = result.get('userName')
                    if user_name:
                        message = f"✅ {user_name}, ¡Tu cita está confirmada! (ID: {confirmation_id})"
                    else:
                        message = f"✅ ¡Cita confirmada! (ID: {confirmation_id})"
                    return True, message
                else:
                    return True, "✅ Reserva confirmada - verifique su correo electrónico"
            elif result.get('success') is False:
                indicator = result.get('indicator', 'unknown')
                return False, f"❌ Error en la reserva: {indicator}"
            else:
                # Unclear result - assume success if no clear errors
                return True, "✅ Reserva procesada - verifique su correo electrónico"
                
        except Exception as e:
            self.logger.error(f"❌ Error checking booking success: {e}")
            return False, f"❌ Error al verificar reserva: {str(e)}"
