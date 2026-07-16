"""Provider-specific handoff playbooks for hard website-control boundaries."""

from __future__ import annotations

from typing import Any

MAX_PLAYBOOK_STEPS = 5

CAPTCHA_PROVIDERS = frozenset({"recaptcha", "hcaptcha", "turnstile", "cloudflare_challenge"})
PAYMENT_PROVIDERS = frozenset({
    "stripe",
    "paypal",
    "razorpay",
    "paytm",
    "cashfree",
    "checkout.com",
    "adyen",
    "square",
    "braintree",
    "mollie",
    "klarna",
    "afterpay",
    "payu",
    "paystack",
    "phonepe",
    "billdesk",
    "authorize.net",
})
CALENDAR_PROVIDERS = frozenset({
    "calendly",
    "acuity",
    "booksy",
    "zocdoc",
    "appointlet",
    "setmore",
    "cal.com",
    "google_calendar",
    "microsoft_bookings",
    "simplybook",
    "tidycal",
    "savvycal",
    "fresha",
})


def handoff_playbook_for(barrier_key: str, provider: str = "", vertical_key: str = "") -> dict[str, Any]:
    """Return a safe handoff playbook for one detected provider boundary."""
    key = _clean_key(barrier_key)
    provider_key = _clean_key(provider)
    if key in {"auth_required", "captcha"}:
        return _auth_or_captcha_playbook(key, provider_key)
    if key == "payment_handoff":
        return _payment_playbook(provider_key)
    if key == "calendar_widget":
        return _calendar_playbook(provider_key, vertical_key)
    if key == "file_upload":
        return _file_upload_playbook()
    if key == "embedded_iframe":
        return _iframe_playbook(provider_key)
    if key == "external_handoff":
        return _external_playbook(provider_key)
    return _generic_playbook()


def _auth_or_captcha_playbook(barrier_key: str, provider: str) -> dict[str, Any]:
    challenge = provider if provider in CAPTCHA_PROVIDERS else "login or challenge"
    return _playbook(
        provider_label=_provider_label(challenge),
        automation_boundary="AI Hub must not collect credentials, bypass login, or solve bot challenges.",
        user_message="Please complete the login or verification step yourself, then return here.",
        admin_action="Connect an authenticated integration or keep this as a human handoff.",
        recovery="After the user finishes verification, refresh discovery or continue from the returned page.",
        steps=[
            "Open the protected page for the user.",
            "Pause automation while the user completes the challenge.",
            "Resume only after the user confirms they are back on the client site.",
        ],
    )


def _payment_playbook(provider: str) -> dict[str, Any]:
    provider_name = provider if provider in PAYMENT_PROVIDERS else "payment provider"
    return _playbook(
        provider_label=_provider_label(provider_name),
        automation_boundary="AI Hub can navigate to checkout, but must not enter payment credentials, OTPs, or submit final payment.",
        user_message="I can open the secure checkout. You complete payment directly with the provider.",
        admin_action="Use provider APIs/webhooks for payment status; never automate card or bank credential entry.",
        recovery="After provider return/webhook confirmation, refresh cart/order status before continuing.",
        steps=[
            "Summarize the order or booking before checkout.",
            "Open the secure checkout or payment provider page.",
            "Let the user complete payment outside automation.",
            "Use return URL, webhook, or admin status to confirm completion.",
        ],
    )


def _calendar_playbook(provider: str, vertical_key: str) -> dict[str, Any]:
    provider_name = provider if provider in CALENDAR_PROVIDERS else "calendar provider"
    owner = "clinic" if vertical_key == "healthcare" else "site team"
    return _playbook(
        provider_label=_provider_label(provider_name),
        automation_boundary="AI Hub may open the scheduler, but should not finalize a regulated appointment slot without explicit user confirmation.",
        user_message="I can open the scheduler. Please choose the slot that works for you.",
        admin_action=f"Connect the {owner} calendar API for automatic availability and confirmation.",
        recovery="After the user confirms a selected slot, record the chosen time or hand off to staff.",
        steps=[
            "Collect preferred date/time constraints in chat.",
            "Open the scheduler or same-origin booking page.",
            "Let the user choose or confirm a slot.",
            "Hand off to staff when provider confirmation is uncertain.",
        ],
    )


def _file_upload_playbook() -> dict[str, Any]:
    return _playbook(
        provider_label="File upload",
        automation_boundary="AI Hub must not fabricate or upload user documents.",
        user_message="Please upload the required file yourself, then I can continue with the next step.",
        admin_action="Provide a secure upload integration with clear consent and retention rules.",
        recovery="Continue only after the site confirms the upload is present.",
        steps=[
            "Explain which file is needed.",
            "Open the upload step.",
            "Wait for the user to upload and confirm.",
        ],
    )


def _iframe_playbook(provider: str) -> dict[str, Any]:
    return _playbook(
        provider_label=_provider_label(provider or "Embedded widget"),
        automation_boundary="Cross-origin iframe contents cannot be controlled safely by the pasted script.",
        user_message="This step opens an embedded provider widget. Please complete the provider step directly.",
        admin_action="Use the provider API/SDK or a first-party integration when deeper control is required.",
        recovery="Refresh page context after the provider widget completes or redirects.",
        steps=[
            "Detect the iframe/provider boundary.",
            "Open or focus the provider-controlled step.",
            "Pause automation until the user or provider returns a completed state.",
        ],
    )


def _external_playbook(provider: str) -> dict[str, Any]:
    return _playbook(
        provider_label=_provider_label(provider or "External provider"),
        automation_boundary="AI Hub cannot control pages after cross-origin navigation unless the destination also installs the widget.",
        user_message="This step opens another provider. I can take you there, then you complete it directly.",
        admin_action="Add a return URL, webhook, or second-site widget install for controlled continuation.",
        recovery="Resume only after the user returns to the client site or a provider callback updates status.",
        steps=[
            "Confirm the cross-origin handoff with the user.",
            "Open the provider link.",
            "Wait for return URL, callback, or user confirmation.",
        ],
    )


def _generic_playbook() -> dict[str, Any]:
    return _playbook(
        provider_label="Human handoff",
        automation_boundary="This step needs human confirmation before automation can continue.",
        user_message="This step needs confirmation. I can open the right page and wait.",
        admin_action="Review the flow evidence and add a provider integration if automatic control is required.",
        recovery="Refresh discovery after the human/provider step completes.",
        steps=["Open the relevant page.", "Pause automation.", "Resume after user or admin confirmation."],
    )


def _playbook(
    *,
    provider_label: str,
    automation_boundary: str,
    user_message: str,
    admin_action: str,
    recovery: str,
    steps: list[str],
) -> dict[str, Any]:
    return {
        "provider_label": provider_label[:120],
        "automation_boundary": automation_boundary[:300],
        "user_message": user_message[:300],
        "admin_action": admin_action[:300],
        "recovery": recovery[:300],
        "playbook_steps": [step[:240] for step in steps[:MAX_PLAYBOOK_STEPS] if step],
    }


def _provider_label(value: str) -> str:
    text = str(value or "").replace("_", " ").strip()
    return text.title() if text else "Provider"


def _clean_key(value: Any) -> str:
    return str(value or "").strip().lower()
