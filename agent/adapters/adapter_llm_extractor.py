"""
Bounded LLM-Assisted Extractor.

For unknown/custom sites, uses OpenAI to detect product schema and CSS
selectors from page HTML samples. Results are validated before saving.

Runs only when LLM_EXTRACTOR_ENABLED=true and Azure OpenAI is configured.
The extractor validates all results before persisting them.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any

import config
from agent.providers.azure_openai import create_chat_completion

logger = logging.getLogger(__name__)

MAX_HTML_SAMPLE_CHARS = 4000
MIN_CONFIDENCE_THRESHOLD = 0.7
SELECTOR_PATTERN = re.compile(r'^[a-zA-Z#.\[\]:\-_\s>+~*="\'^$|,()0-9]+$')
EXTRACTION_SYSTEM_PROMPT = (
    "You are an ecommerce HTML analyzer. Given a sample of an ecommerce product page HTML, "
    "identify the CSS selectors for key product elements. Return ONLY a JSON object with these keys:\n"
    '- "product_name": CSS selector for the product name/title\n'
    '- "product_price": CSS selector for the product price\n'
    '- "product_image": CSS selector for the main product image\n'
    '- "add_to_cart": CSS selector for the add-to-cart button (or null)\n'
    '- "variant_select": CSS selector for variant/option selectors like size/color (or null)\n'
    '- "confidence": your confidence from 0.0 to 1.0 that these selectors are correct\n'
    "Return ONLY valid JSON, no markdown, no explanation."
)
EXTRACTION_MAX_TOKENS = 300


@dataclass
class ExtractedSelectors:
    """Result of LLM-assisted selector extraction."""

    product_name: str
    product_price: str
    product_image: str
    add_to_cart: str | None
    variant_select: str | None
    confidence: float
    validated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_valid_css_selector(selector: str | None) -> bool:
    """Check whether a string looks like a valid CSS selector."""
    if not selector or not isinstance(selector, str):
        return False
    clean = selector.strip()
    if not clean or len(clean) > 200:
        return False
    return bool(SELECTOR_PATTERN.match(clean))


def _validate_selectors_against_html(
    selectors: dict[str, Any],
    html: str,
) -> bool:
    """Validate that extracted selectors plausibly match the HTML sample."""
    required_keys = ("product_name", "product_price", "product_image")
    for key in required_keys:
        value = selectors.get(key)
        if not value or not isinstance(value, str):
            return False
        if not _is_valid_css_selector(value):
            return False
        # Basic sanity: the selector's primary element/class/id should appear in HTML
        fragments = re.findall(r'[a-zA-Z][\w-]*', value)
        if fragments and not any(frag in html for frag in fragments[:3]):
            logger.debug("Selector fragment %s not found in HTML for key %s", fragments[:3], key)
            return False

    return True


def extract_selectors_from_html(
    html_sample: str,
    site_id: str,
) -> ExtractedSelectors | None:
    """
    Use OpenAI to extract CSS selectors from a product page HTML sample.

    Returns validated ExtractedSelectors, or None if extraction/validation fails.
    """
    if not config.LLM_EXTRACTOR_ENABLED:
        logger.info("LLM extractor skipped: LLM_EXTRACTOR_ENABLED is false.")
        return None
    if not config.AZURE_OPENAI_API_KEY:
        logger.info("LLM extractor skipped: Azure OpenAI is not configured.")
        return None

    truncated_html = html_sample[:MAX_HTML_SAMPLE_CHARS]
    if not truncated_html.strip():
        return None

    try:
        raw_response = create_chat_completion(
            [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": truncated_html},
            ],
            max_completion_tokens=EXTRACTION_MAX_TOKENS,
            json_response=True,
        )
        logger.debug("LLM extractor raw response for %s: %s", site_id, raw_response[:200])

        # Strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)

        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            logger.warning("LLM extractor returned non-dict for %s", site_id)
            return None

    except json.JSONDecodeError as exc:
        logger.warning("LLM extractor JSON parse failed for %s: %s", site_id, exc)
        return None
    except Exception as exc:
        logger.warning("LLM extractor Azure call failed for %s: %s", site_id, exc)
        return None

    # Validate extracted selectors
    confidence = float(parsed.get("confidence", 0.0))
    validated = _validate_selectors_against_html(parsed, truncated_html)

    if not validated:
        logger.info("LLM extractor selectors failed validation for %s", site_id)
        confidence = min(confidence, 0.3)

    if confidence < MIN_CONFIDENCE_THRESHOLD and validated:
        # LLM was uncertain but selectors look valid; accept with reduced confidence
        confidence = max(confidence, MIN_CONFIDENCE_THRESHOLD)

    result = ExtractedSelectors(
        product_name=str(parsed.get("product_name") or ""),
        product_price=str(parsed.get("product_price") or ""),
        product_image=str(parsed.get("product_image") or ""),
        add_to_cart=parsed.get("add_to_cart") if _is_valid_css_selector(parsed.get("add_to_cart")) else None,
        variant_select=parsed.get("variant_select") if _is_valid_css_selector(parsed.get("variant_select")) else None,
        confidence=round(min(max(confidence, 0.0), 1.0), 2),
        validated=validated,
    )

    logger.info(
        "LLM extractor for %s: confidence=%.2f validated=%s name=%s price=%s",
        site_id,
        result.confidence,
        result.validated,
        result.product_name,
        result.product_price,
    )

    return result


def extract_and_save(
    html_sample: str,
    site_id: str,
) -> ExtractedSelectors | None:
    """Extract selectors and persist them if validated with sufficient confidence."""
    from db.admin_domain import admin_facade as admin_db

    result = extract_selectors_from_html(html_sample, site_id)
    if result is None:
        return None

    if result.validated and result.confidence >= MIN_CONFIDENCE_THRESHOLD:
        admin_db.save_site_selectors(
            site_id=site_id,
            selectors=result.to_dict(),
            confidence=result.confidence,
            validated=result.validated,
        )
        logger.info("Saved validated selectors for %s (confidence=%.2f)", site_id, result.confidence)
    else:
        logger.info(
            "Selectors for %s not saved: validated=%s confidence=%.2f",
            site_id,
            result.validated,
            result.confidence,
        )

    return result
