# Imports.
from decouple import config


# Custom class for handling environment secrets.
class Secrets:
    def __init__(self) -> None:
        self.time_period_days: int = config("TIME_PERIOD_DAYS", cast=int)
        self.test_mode: bool = config("TEST_MODE", cast=bool)

        self.github_org_name: str = config("GITHUB_ORG_NAME", cast=str)
        self.github_token: str = config("GITHUB_TOKEN", cast=str)

        if self.test_mode:
            self.twitter_key: str = config("TWITTER_KEY", cast=str)
            self.twitter_secret: str = config("TWITTER_SECRET", cast=str)
            self.twitter_access_token: str = config("TWITTER_ACCESS_TOKEN", cast=str)
            self.twitter_access_secret: str = config("TWITTER_ACCESS_SECRET", cast=str)

            self.discord_hook: str = config("DISCORD_HOOK", cast=str)
