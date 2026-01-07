from playwright.async_api import Page
import random

async def inject_stealth(page: Page):
    """
    Injects javascript to hide automation flags.
    """
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
    """)

    # Randomize hardware concurrency
    concurrency = random.randint(2, 8)
    await page.add_init_script(f"""
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {concurrency},
        }});
    """)

    # Mock plugins
    await page.add_init_script("""
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
    """)

    # Mock languages
    await page.add_init_script("""
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
    """)

    # Mask WebGL Vendor
    await page.add_init_script("""
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter(parameter);
        };
    """)
