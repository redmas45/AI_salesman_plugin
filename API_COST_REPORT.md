# AI Hub API Cost Report

Prepared: 2026-07-01

This report estimates provider API cost for 100 users completing one Maya sales conversation each. The estimate is domain-independent: ecommerce, insurance, finance, healthcare, food, real estate, education, automotive, legal services, recruiting, events, construction, travel, and generic sites all use the same runtime pricing structure. Domain changes affect prompt size and answer length, not the billing model.

## Current Runtime Path

The current project configuration uses:

| Stage | Current provider | Current model path | Billing unit |
| --- | --- | --- | --- |
| Speech to text | Groq | `whisper-large-v3-turbo` | Per hour transcribed, 10-second minimum per request |
| Sales reasoning | OpenAI | `gpt-4o-mini` | Input and output text tokens |
| Text to speech | Groq | `canopylabs/orpheus-v1-english` | Characters generated |
| OpenAI TTS fallback | OpenAI | `tts-1` under current fast voice config | Characters generated |

Important: the CRM "tokens used" number is a local estimate from customer transcript plus Maya response text. It is useful for client/session budgets, but it is not the exact OpenAI/Groq invoice amount because provider-side prompt tokens, cached tokens, audio seconds, and TTS audio generation are billed separately.

## Price Inputs

Official pricing checked on 2026-07-01:

| Provider | Model/service | Price used |
| --- | --- | --- |
| OpenAI | `gpt-4o-mini` | $0.15 / 1M input tokens, $0.60 / 1M output tokens |
| OpenAI | `gpt-4o-mini-transcribe` | Estimated $0.003 / minute |
| OpenAI | `tts-1` | $15.00 / 1M characters |
| OpenAI | `gpt-4o-mini-tts` | $0.60 / 1M text input tokens, $12.00 / 1M audio output tokens |
| Groq | `whisper-large-v3-turbo` | $0.04 / hour transcribed, 10-second minimum per request |
| Groq | `canopylabs/orpheus-v1-english` | $22.00 / 1M characters |
| Groq | `openai/gpt-oss-20b` alternative LLM | $0.075 / 1M input tokens, $0.30 / 1M output tokens |
| Groq | `openai/gpt-oss-120b` alternative LLM | $0.15 / 1M input tokens, $0.60 / 1M output tokens |
| ElevenLabs | Text to Speech, Flash/Turbo | $0.05 / 1,000 characters |
| ElevenLabs | Text to Speech, Multilingual v2/v3 | $0.10 / 1,000 characters |
| ElevenLabs | Speech to Text, Scribe | $0.22 / hour of audio |
| ElevenLabs | Speech to Text, Scribe realtime | $0.39 / hour of audio |
| Sarvam AI | Speech to Text | Rs.30 / hour of audio |
| Sarvam AI | Speech to Text + Translate | Rs.30 / hour of audio |
| Sarvam AI | Text to Speech, Bulbul v2 | Rs.15 / 10,000 characters |
| Sarvam AI | Text to Speech, Bulbul v3 | Rs.30 / 10,000 characters |
| Sarvam AI | Translate V1 | Rs.20 / 10,000 characters |
| Sarvam AI | Sarvam-30B chat | Rs.2.5 / 1M input tokens, Rs.1.5 / 1M cached input tokens, Rs.10 / 1M output tokens |
| Sarvam AI | Sarvam-105B chat | Rs.4 / 1M input tokens, Rs.2.5 / 1M cached input tokens, Rs.16 / 1M output tokens |

Sources:

- OpenAI `gpt-4o-mini` model page: https://developers.openai.com/api/docs/models/gpt-4o-mini
- OpenAI API pricing page: https://developers.openai.com/api/docs/pricing
- OpenAI `tts-1` model page: https://developers.openai.com/api/docs/models/tts-1
- OpenAI `gpt-4o-mini-tts` model page: https://developers.openai.com/api/docs/models/gpt-4o-mini-tts
- Groq pricing page: https://groq.com/pricing
- ElevenLabs API pricing page: https://elevenlabs.io/pricing/api
- Sarvam AI API pricing page: https://www.sarvam.ai/api-pricing
- Sarvam API docs pricing page: https://docs.sarvam.ai/api-reference-docs/pricing

## Usage Assumptions

The user phrase "4-5 sentences" is treated as 4-5 user turns per customer. Each turn includes:

1. User speaks one sentence.
2. STT transcribes the audio.
3. Maya sends one LLM request with system prompt, vertical context, RAG/page context, cart/profile context, and recent history.
4. Maya replies with text and TTS audio.

| Scenario | Users | Turns/user | Total turns | User audio/turn | Maya reply chars/turn | LLM input tokens/turn | LLM output tokens/turn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lean | 100 | 4 | 400 | 4 sec | 180 | 1,500 | 120 |
| Base | 100 | 5 | 500 | 5 sec | 250 | 2,500 | 180 |
| Heavy | 100 | 5 | 500 | 8 sec | 450 | 6,000 | 320 |

The heavy case covers longer vertical prompts, more history, larger catalog/plan context, and more detailed sales explanations.

## Cost Estimate: Current Hybrid Path

Current path = Groq STT + OpenAI `gpt-4o-mini` LLM + Groq Orpheus TTS.

| Scenario | OpenAI LLM | Groq STT | Groq TTS | Total for 100 users | Cost/user |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lean | $0.119 | $0.044 | $1.584 | $1.747 | $0.017 |
| Base | $0.242 | $0.056 | $2.750 | $3.048 | $0.030 |
| Heavy | $0.546 | $0.056 | $4.950 | $5.552 | $0.056 |

Base calculation:

- LLM input: 500 turns x 2,500 tokens = 1,250,000 input tokens x $0.15 / 1M = $0.1875.
- LLM output: 500 turns x 180 tokens = 90,000 output tokens x $0.60 / 1M = $0.0540.
- Groq STT: 500 requests x 10-second minimum = 5,000 billable seconds = 1.389 hours x $0.04 = $0.0556.
- Groq TTS: 500 replies x 250 chars = 125,000 chars x $22 / 1M = $2.7500.
- Total: about $3.05 for 100 completed sales conversations.

## Cost Estimate: OpenAI-Only Fallback Path

OpenAI-only path = OpenAI `gpt-4o-mini-transcribe` + OpenAI `gpt-4o-mini` LLM + OpenAI `tts-1`.

| Scenario | OpenAI LLM | OpenAI STT | OpenAI TTS `tts-1` | Total for 100 users | Cost/user |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lean | $0.119 | $0.080 | $1.080 | $1.279 | $0.013 |
| Base | $0.242 | $0.125 | $1.875 | $2.242 | $0.022 |
| Heavy | $0.546 | $0.200 | $3.375 | $4.121 | $0.041 |

OpenAI-only is cheaper in this estimate mainly because `tts-1` is $15 / 1M characters while Groq Orpheus English is $22 / 1M characters. Groq still has a cheaper STT rate and may be preferred for speed or voice quality, but TTS dominates this workload.

## Future Multilingual Provider Comparison

These providers are not part of the current runtime path. They are listed only for future multilingual cost comparison.

Planning exchange-rate assumption for Sarvam comparison: Rs.85 = $1. This is only for planning; actual billing remains in INR.

Base usage for this comparison:

- 100 users.
- 5 turns per user.
- 500 total voice turns.
- 2,500 seconds of user audio.
- 125,000 Maya TTS output characters.
- OpenAI `gpt-4o-mini` remains the LLM at about $0.242 for the base case unless we explicitly replace the LLM too.

| Future audio provider path | STT cost | TTS cost | OpenAI LLM cost | Estimated total for 100 users | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| ElevenLabs Scribe + Flash/Turbo TTS | $0.153 | $6.250 | $0.242 | $6.645 | Lower ElevenLabs TTS cost path; useful for broad multilingual voices. |
| ElevenLabs Scribe + Multilingual v2/v3 TTS | $0.153 | $12.500 | $0.242 | $12.895 | Higher quality/multilingual path; much more expensive than current Groq/OpenAI audio. |
| ElevenLabs Scribe realtime + Flash/Turbo TTS | $0.271 | $6.250 | $0.242 | $6.763 | Realtime STT raises STT cost slightly, but TTS is still the main spend. |
| Sarvam STT + Bulbul v2 TTS | about Rs.20.83 / $0.25 | about Rs.187.50 / $2.21 | $0.242 | about $2.69 | Strong future option for Indian-language coverage if voice quality fits. |
| Sarvam STT + Bulbul v3 TTS | about Rs.20.83 / $0.25 | about Rs.375.00 / $4.41 | $0.242 | about $4.90 | Higher Sarvam TTS quality path; still competitive for Indian languages. |

Sarvam also has translation APIs. If we need separate translation instead of native multilingual STT/TTS, add Rs.20 per 10,000 translated characters. For a voice-sales flow, native STT/TTS in the target language is cleaner than translating every turn unless the sales brain must stay English-only internally.

## Groq LLM Alternative

The current app does not route LLM calls to Groq. It uses Groq for audio and OpenAI for the LLM. If we later add a Groq LLM provider:

| LLM provider/model | Base LLM cost for 500 turns | Difference vs current OpenAI LLM |
| --- | ---: | ---: |
| OpenAI `gpt-4o-mini` | $0.242 | Current |
| Groq `openai/gpt-oss-120b` | $0.242 | Same price on listed rates |
| Groq `openai/gpt-oss-20b` | $0.121 | Saves about $0.12 per 100 users |

Switching the LLM alone will not materially change total cost because TTS is the dominant spend. In the base current hybrid case, Groq TTS is about 90% of the provider bill.

## Monthly Projection

If this traffic repeats daily:

| Traffic | Current hybrid total/day | Current hybrid total/month, 30 days | OpenAI-only total/month, 30 days |
| --- | ---: | ---: | ---: |
| 100 users/day, lean | $1.75 | $52.41 | $38.37 |
| 100 users/day, base | $3.05 | $91.43 | $67.26 |
| 100 users/day, heavy | $5.55 | $166.56 | $123.63 |

If there are 100 users total per month, use the single-run numbers instead: about $1.75-$5.55/month for the current hybrid path, with a base estimate of about $3.05/month.

## Budget Recommendation

For early testing with 100 users/day, a practical monthly provider budget is:

| Budget | What it covers |
| --- | --- |
| $50/month | Lean traffic or light testing. Tight if replies are long. |
| $100/month | Good base budget for 100 users/day with current hybrid audio. |
| $200/month | Safer testing budget for longer answers, retries, failed turns, and heavier vertical context. |

Recommended CRM setting for now: set `OPENAI_MONTHLY_BUDGET_USD` to at least `100` for a 100-users/day test. This only tracks OpenAI cost reporting when `OPENAI_ADMIN_KEY` is configured; Groq cost must still be monitored through Groq billing or a future Groq billing integration.
