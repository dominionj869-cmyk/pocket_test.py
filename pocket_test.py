import os
import time
import logging
import requests

from pocketoptionapi.stable_api import PocketOption


# ============================================================
# CONFIG
# ============================================================

PO_SSID = os.getenv("PO_SSID", "").strip()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

ASSET = "EURUSD_otc"
PERIOD = 60

# Connection/data test ONLY.
# No trading is performed anywhere in this file.
NO_TRADING = True


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# ============================================================
# TELEGRAM
# ============================================================

def telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram secrets are not configured.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
            },
            timeout=20,
        )

        response.raise_for_status()

    except Exception as exc:
        logging.error("Telegram error: %s", exc)


# ============================================================
# MAIN
# ============================================================

def main():

    logging.info("=" * 60)
    logging.info("POCKET OPTION DEMO CONNECTION TEST")
    logging.info("NO TRADING")
    logging.info("=" * 60)

    if not PO_SSID:
        message = (
            "🔴 POCKET OPTION TEST FAILED\n\n"
            "Missing GitHub Secret: PO_SSID\n\n"
            "No connection was attempted.\n"
            "NO TRADING."
        )

        logging.error(message)
        telegram(message)
        return 1

    try:
        # ----------------------------------------------------
        # CREATE CLIENT
        # ----------------------------------------------------

        logging.info("Creating Pocket Option client...")

        api = PocketOption(PO_SSID)

        # ----------------------------------------------------
        # CONNECT
        # ----------------------------------------------------

        logging.info("Connecting to Pocket Option...")

        ok, error = api.connect()

        if not ok:

            message = (
                "🔴 POCKET OPTION CONNECTION FAILED\n\n"
                f"Reason: {error}\n\n"
                "NO TRADE WAS PLACED."
            )

            logging.error(message)
            telegram(message)
            return 1

        logging.info("WebSocket connection established.")

        # ----------------------------------------------------
        # WAIT FOR TIME SYNC
        # ----------------------------------------------------

        logging.info("Waiting for server time synchronization...")

        deadline = time.time() + 30

        while time.time() < deadline:

            if api.check_connect() and api.is_time_synced():
                break

            time.sleep(0.25)

        if not api.check_connect():

            message = (
                "🔴 POCKET OPTION TEST FAILED\n\n"
                "WebSocket disconnected before synchronization.\n\n"
                "NO TRADE WAS PLACED."
            )

            logging.error(message)
            telegram(message)
            return 1

        if not api.is_time_synced():

            message = (
                "🔴 POCKET OPTION TEST FAILED\n\n"
                "Server time synchronization timed out.\n\n"
                "NO TRADE WAS PLACED."
            )

            logging.error(message)
            telegram(message)
            return 1

        logging.info("Server time synchronized.")

        # ----------------------------------------------------
        # BALANCE
        # ----------------------------------------------------

        balance = api.get_balance()

        logging.info("Demo balance: %s", balance)

        # ----------------------------------------------------
        # ASSETS
        # ----------------------------------------------------

        assets = api.get_assets()

        asset_count = len(assets) if assets else 0

        logging.info("Assets loaded: %s", asset_count)

        # ----------------------------------------------------
        # FIND EURUSD OTC
        # ----------------------------------------------------

        eurusd = None

        if assets:

            for asset in assets:

                if isinstance(asset, dict):

                    symbol = (
                        asset.get("symbol")
                        or asset.get("asset")
                        or asset.get("name")
                    )

                    if symbol == ASSET:
                        eurusd = asset
                        break

        # ----------------------------------------------------
        # PAYOUT
        # ----------------------------------------------------

        payout = api.get_payout(ASSET)

        logging.info("%s payout: %s%%", ASSET, payout)

        # ----------------------------------------------------
        # SUBSCRIBE TO MARKET
        # ----------------------------------------------------

        logging.info(
            "Subscribing to %s at %s-second candles...",
            ASSET,
            PERIOD,
        )

        subscribed = api.subscribe(
            ASSET,
            PERIOD,
        )

        if not subscribed:

            message = (
                "🟠 POCKET OPTION CONNECTED\n\n"
                f"Balance: {balance}\n"
                f"Assets loaded: {asset_count}\n"
                f"Asset: {ASSET}\n"
                f"Payout: {payout}%\n\n"
                "⚠️ Asset subscription failed.\n"
                "NO TRADE WAS PLACED."
            )

            logging.warning(message)
            telegram(message)
            return 1

        # Give the stream a moment to populate.
        time.sleep(3)

        # ----------------------------------------------------
        # SENTIMENT
        # ----------------------------------------------------

        try:
            sentiment = api.get_sentiment(ASSET)
        except Exception:
            sentiment = None

        logging.info(
            "%s sentiment: %s",
            ASSET,
            sentiment,
        )

        # ----------------------------------------------------
        # LIVE TICKS
        # ----------------------------------------------------

        try:
            ticks = api.get_realtime_ticks(
                ASSET,
                limit=5,
            )
        except Exception:
            ticks = []

        logging.info(
            "Received %s recent ticks.",
            len(ticks),
        )

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        if eurusd is not None:

            asset_status = "FOUND"

        else:

            asset_status = "NOT FOUND IN CATALOG"

        message = (
            "🟢 POCKET OPTION DEMO CONNECTION SUCCESS\n\n"
            "Authentication: CONNECTED\n"
            "WebSocket: CONNECTED\n"
            f"Demo Balance: {balance}\n"
            f"Assets Loaded: {asset_count}\n\n"
            f"Asset: {ASSET}\n"
            f"Asset Catalog: {asset_status}\n"
            f"Payout: {payout}%\n"
            f"Sentiment: {sentiment}\n"
            f"Live Ticks: {len(ticks)}\n\n"
            "Candle Period: 1 minute\n"
            "Trading: OFF\n"
            "NO TRADE WAS PLACED."
        )

        logging.info("\n%s", message)
        telegram(message)

        # ----------------------------------------------------
        # KEEP CONNECTION ALIVE BRIEFLY
        # ----------------------------------------------------

        logging.info("Connection test complete.")

        for remaining in range(10, 0, -1):

            if not api.check_connect():
                logging.warning("WebSocket disconnected.")
                break

            logging.info(
                "Connection alive... %s seconds",
                remaining,
            )

            time.sleep(1)

        logging.info("Pocket Option test finished.")

        return 0

    except Exception as exc:

        logging.exception(
            "Pocket Option test crashed."
        )

        message = (
            "🔴 POCKET OPTION TEST ERROR\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            "NO TRADE WAS PLACED."
        )

        telegram(message)

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
