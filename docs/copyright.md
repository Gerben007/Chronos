# Copyright & licensing

Chronos hosts no third-party copyrighted text or media. We **link** to
resources stored in Nextcloud and shared by the contributors who uploaded
them. Bible text shown on-page is from public-domain translations.

## Bible translations

| Translation | Status            | Use                                        |
|-------------|-------------------|--------------------------------------------|
| KJV         | Public domain     | English views, default                     |
| ESV         | Crossway licence  | English views, after written approval only |
| 1933/53 OAV | Public domain     | Afrikaans views                            |

`ENGLISH_BIBLE` env var switches `kjv` → `esv` once approval is in hand.
No ESV verse text may be loaded into `bible_verses` before that approval.

## Classical Conversations "Fridge Facts"

CC materials are **linked only**, never copied or paraphrased into entry
content. Links resolve to the contributor's Nextcloud share. If CC
requests removal of any link:

1. Mark the file row `status='quarantined'` and `public_url=NULL`.
2. Run the fast-path rewrite to drop the link from entry JSON.
3. Email confirmation within 7 days.

Our own AI-paraphrased file summaries are short, transformative, and
attribute the file (filename + uploader). They are not a substitute for
the original.

## Artwork

Wikimedia Commons only. Each entry's `artwork_credit` field must carry
the author / licence string per Commons' attribution requirements. If a
licence is unclear, we omit the image rather than guess.

## User-generated content

Files uploaded by mothers via Nextcloud remain the property of the
uploader. Sharing them via Chronos implies a non-exclusive licence for
us to surface and link, revocable at any time by request.

## Removal requests

Email `security@stratusfinance.co.za` (yes, same address as security —
small team). Confirm within 7 business days.
