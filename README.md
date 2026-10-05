# Polititrace Nigeria — Daily Politics & Society Intelligence Dispatcher

Automated 24/7 briefing and dispatch engine monitoring Nigerian national politics, state governance corridors, talk radio citizen voices, and macroeconomic indicators.

## Features
- **Verified News Feeds:** Ingests breaking investigative and policy news from *Premium Times*, *The Punch*, *The Cable*, and *Vanguard*.
- **Talk Radio Ground Sentiments:** Direct citizen quotes from Lagos Info 99.3 FM, Abuja Brekete 101.1 FM, Edo ITV 92.3 FM, and Rivers Info 92.3 FM.
- **Macroeconomic Reality Ledger:** Tracks PMS petrol pump rates across state corridors, parallel & NAFEM FX rates, staple food prices, and national electricity grid generation (MW).
- **Daily Automated Email Briefing:** Dispatches a high-contrast, publication-ready email digest to subscribers every morning at 06:00 WAT via GitHub Actions and Gmail SMTP.

## GitHub Actions Secrets Required
- `MAIL_USERNAME`: Gmail address used for sending digests.
- `MAIL_PASSWORD`: Google App Password for SMTP authentication.
- `MAIL_TO`: Destination email address for receiving daily digests (defaults to `MAIL_USERNAME`).
