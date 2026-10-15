import logging
from urllib.parse import unquote


class OmitWebhookVerification(logging.Filter):
    def filter(self, record):
        # Meta's verification token is a query parameter. Never print its request line.
        return "verify_token" not in unquote(record.getMessage()).casefold()
