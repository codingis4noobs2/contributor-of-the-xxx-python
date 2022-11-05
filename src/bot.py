# Imports.
import asyncio
import logging
from datetime import datetime
from typing import Any

import aiocron
import aiohttp
from PIL import Image

from src import secrets
from src.models import Contributor, Organization

logging.basicConfig(level=logging.INFO)


class Bot:
    def __init__(self) -> None:
        pass

    async def get_contributor(self) -> Contributor | None:
        """
        GET top contributor data by making a simple request to GitHub's REST API.
        """

        contributors = {}
        bots = []
        headers = {"Authorization": f"token {secrets.github_token}"}

        async with aiohttp.ClientSession(headers=headers) as session:
            org_name = secrets.github_org_name
            org_api = f"https://api.github.com/orgs/{org_name}"

            try:
                async with session.get(org_api) as response:
                    data = await response.json()
                    organization = Organization(
                        login=data["login"],
                        avatar_url=data["avatar_url"],
                    )
            except Exception as e:
                logging.error(f"{datetime.now()} -> Unable to fetch data\nError: {e}")
                return None

            # get PRs
            for page in range(1, 100):
                api = "https://api.github.com/search/issues" + f"?q=org:{org_name} is:pull-request is:merged&sort=created&per_page=100&page={page}"

                async with session.get(api) as response:
                    data = await response.json()

                if not data.get("items"):
                    break

                for item in data["items"]:
                    handle = item["user"]["login"]
                    pull = item["pull_request"]
                    if pull["merged_at"] is not None:
                        difference = datetime.utcnow() - datetime.fromisoformat(pull["merged_at"][0:10])

                        if difference.days > int(secrets.time_period_days):
                            break

                        if handle not in list(contributors.keys()) + bots + secrets.excluded_profiles:
                            user_api = f"https://api.github.com/users/{handle}"
                            async with session.get(user_api) as response:
                                data = await response.json()
                            contributors[handle] = Contributor(data, organization=organization)
                            if data["type"] == "Bot":
                                bots += data["login"]
                        if handle in contributors:
                            contributors[handle].pr_count += 1

            # get Issues
            for page in range(1, 100):
                api = "https://api.github.com/search/issues" + f"?q=org:{org_name} is:issue&sort=created&per_page=100&page={page}"

                async with session.get(api) as response:
                    data = await response.json()

                if not data.get("items"):
                    break

                for item in data["items"]:
                    handle = item["user"]["login"]
                    difference = datetime.utcnow() - datetime.fromisoformat(item["created_at"][0:10])

                    if difference.days > int(secrets.time_period_days):
                        break

                    if handle not in list(contributors.keys()) + bots + secrets.excluded_profiles:
                        user_api = f"https://api.github.com/users/{handle}"
                        async with session.get(user_api) as response:
                            data = await response.json()
                        contributors[handle] = Contributor(data, organization=organization)
                        if data["type"] == "Bot":
                            bots += data["login"]
                    if handle in contributors:
                        contributors[handle].issue_count += 1

        contributors = sorted(contributors.items(), key=lambda x: x[1].pr_count, reverse=True)

        if contributors:
            return contributors[0][1]
        else:
            return None

    def get_contributor_before_run(func) -> Any:
        """
        A simple decorator to return top contributor data retrieved from GitHub's REST API.
        """

        async def wrapper(self):
            print(datetime.now())
            data = await self.get_contributor()
            return await func(self, data)

        return wrapper

    @get_contributor_before_run
    async def run_once(self, contributor: Contributor) -> None:
        """
        Shows the avatar of the top contributor.
        """
        if contributor:
            image = await contributor.generate_image()
            if not secrets.test_mode:
                try:
                    await contributor.post_to_discord()
                    await contributor.post_to_twitter()
                except Exception as e:
                    logging.error(f"{datetime.now()} -> Cannot post to Discord or Twitter\nError: {e}")
            else:
                file_name = "test_image.png"
                image.save(file_name)

                preview = Image.open(file_name)
                preview.show()

            logging.info(f"{datetime.now()} -> Top Contributor: {contributor.login}")

        else:
            logging.info(f"{datetime.now()} -> No contributor for the given time period.")
        print(datetime.now())

    @staticmethod
    @aiocron.crontab(f"0 0 */{secrets.time_period_days} * *")
    async def every() -> None:
        bot = Bot()
        await bot.run_once()

    def run(self, *, run_at_start: bool = False) -> None:
        if run_at_start:
            asyncio.get_event_loop().run_until_complete(self.run_once())

        asyncio.get_event_loop().run_forever()
