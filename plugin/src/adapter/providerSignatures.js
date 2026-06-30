const DEFAULT_PROVIDER_MATCH_LIMIT = 10;

export const PAYMENT_PROVIDER_SIGNATURES = Object.freeze([
  signature("stripe", ["stripe", "stripe.com", "checkout.stripe.com", "js.stripe.com"]),
  signature("paypal", ["paypal", "paypal.com", "paypalobjects.com"]),
  signature("razorpay", ["razorpay", "checkout.razorpay.com"]),
  signature("paytm", ["paytm", "securegw.paytm.in"]),
  signature("cashfree", ["cashfree", "cashfree.com"]),
  signature("checkout.com", ["checkout.com", "cko-session-id"]),
  signature("adyen", ["adyen", "checkoutshopper"]),
  signature("square", ["squareup", "squarecdn", "square.site"]),
  signature("braintree", ["braintree", "braintreegateway"]),
  signature("mollie", ["mollie", "mollie.com"]),
  signature("klarna", ["klarna", "klarna.com"]),
  signature("afterpay", ["afterpay", "afterpay.com", "clearpay"]),
  signature("payu", ["payu", "payu.in", "payu.com"]),
  signature("paystack", ["paystack", "paystack.co"]),
  signature("phonepe", ["phonepe", "phonepe.com"]),
  signature("billdesk", ["billdesk", "billdesk.com"]),
  signature("authorize.net", ["authorize.net", "accept.authorize.net"]),
]);

export const CALENDAR_PROVIDER_SIGNATURES = Object.freeze([
  signature("calendly", ["calendly", "calendly.com"]),
  signature("acuity", ["acuityscheduling", "squarespace scheduling"]),
  signature("booksy", ["booksy", "booksy.com"]),
  signature("zocdoc", ["zocdoc", "zocdoc.com"]),
  signature("appointlet", ["appointlet", "appointlet.com"]),
  signature("setmore", ["setmore", "setmore.com"]),
  signature("cal.com", ["cal.com", "calcom"]),
  signature("google_calendar", ["calendar.google.com", "google calendar"]),
  signature("microsoft_bookings", ["microsoft bookings", "outlook.office365.com/book"]),
  signature("simplybook", ["simplybook", "simplybook.me"]),
  signature("tidycal", ["tidycal", "tidycal.com"]),
  signature("savvycal", ["savvycal", "savvycal.com"]),
  signature("fresha", ["fresha", "fresha.com"]),
]);

export const MAP_PROVIDER_SIGNATURES = Object.freeze([
  signature("google_maps", ["google.com/maps", "maps.googleapis", "maps.google"]),
  signature("mapbox", ["mapbox", "mapbox.com"]),
  signature("openstreetmap", ["openstreetmap", "osm.org"]),
  signature("leaflet", ["leaflet", "leafletjs"]),
  signature("here_maps", ["here.com", "hereapi", "wego.here.com"]),
  signature("bing_maps", ["bing.com/maps", "virtualearth"]),
  signature("mappls", ["mappls", "mapmyindia"]),
]);

export const CONTACT_PROVIDER_SIGNATURES = Object.freeze([
  signature("whatsapp", ["wa.me", "api.whatsapp.com", "web.whatsapp.com"]),
  signature("telegram", ["t.me/", "telegram.me"]),
  signature("messenger", ["m.me/", "messenger.com/t"]),
  signature("zendesk", ["zendesk.com", "zdassets.com/hc"]),
  signature("intercom", ["intercom.help", "intercom.com"]),
  signature("freshchat", ["freshchat.com"]),
]);

export const CAPTCHA_PROVIDER_SIGNATURES = Object.freeze([
  signature("recaptcha", ["recaptcha", "g-recaptcha", "google.com/recaptcha"]),
  signature("hcaptcha", ["hcaptcha", "h-captcha"]),
  signature("turnstile", ["turnstile", "challenges.cloudflare.com"]),
  signature("cloudflare_challenge", ["cf-chl", "cloudflare challenge"]),
]);

function signature(name, tokens) {
  return { name, tokens };
}

export function providerMatchesText(value, signatures, limit = DEFAULT_PROVIDER_MATCH_LIMIT) {
  const text = cleanProviderText(value);
  return signatures
    .filter((provider) => provider.tokens.some((token) => text.includes(token)))
    .map((provider) => provider.name)
    .slice(0, limit);
}

export function cleanProviderText(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}
