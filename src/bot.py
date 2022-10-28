# Imports.
import asyncio
import logging
from datetime import datetime
from typing import Any

import aiocron
import aiohttp

from models import Contributor, Organization

from . import global_


class Bot:
    def __init__(self) -> None:
        pass

    async def get_data(self) -> Any:
        """
        GET github data by making a simple request to GitHub's REST API.
        """

        contributors = {}
        headers = {"Authorization": f"token {global_.GITHUB['TOKEN']}"}

        async with aiohttp.ClientSession(headers=headers) as session:
            org_name = global_.GITHUB["ORG_NAME"]
            api = f"https://api.github.com/orgs/{org_name}/repos"

            async with session.get(api) as response:
                data = await response.json()
                repos = [repo["name"] for repo in data]

                organization = Organization(
                    login=data[0]["owner"]["login"],
                    avatar_url=data[0]["owner"]["avatar_url"],
                )

            for repo in repos:

                for page in range(1, 100):
                    api = (
                        f"https://api.github.com/repos/{org_name}/{repo}/pulls"
                        + f"?state=closed&per_page=100&page={page}"
                    )

                    async with session.get(api) as response:
                        data = await response.json()

                        if not data:
                            break

                        for pull in data:
                            if pull["merged_at"] is not None:
                                handle = pull["user"]["login"]
                                difference = datetime.utcnow() - datetime.fromisoformat(
                                    pull["merged_at"][0:10]
                                )

                                if difference.days > int(global_.TIME_PERIOD_DAYS):
                                    break

                                if handle not in contributors:
                                    api = f"https://api.github.com/users/{handle}"
                                    async with session.get(api) as response:
                                        data = await response.json()
                                    contributors[handle] = Contributor(
                                        data, organization=organization
                                    )

                                contributors[handle].pr_count = (
                                    contributors[handle].pr_count + 1
                                    if handle in contributors
                                    else 1
                                )

                for page in range(1, 100):
                    api = (
                        f"https://api.github.com/repos/{org_name}/{repo}/issues"
                        + f"?state=all&per_page=100&page={page}"
                    )

                    async with session.get(api) as response:
                        data = await response.json()

                        if not data:
                            break

                        for issue in data:
                            if not issue.get("pull_request"):
                                handle = issue["user"]["login"]
                                difference = datetime.utcnow() - datetime.fromisoformat(
                                    issue["created_at"][0:10]
                                )

                                if difference.days > int(global_.TIME_PERIOD_DAYS):
                                    break

                                if handle in contributors:
                                    contributors[handle].issue_count = (
                                        contributors[handle].issue_count + 1
                                    )

        contributors = sorted(
            contributors.items(), key=lambda x: x[1].pr_count, reverse=True
        )
        if contributors:
            return contributors[0][1]
        return None

    def get_contributor_before_run(func) -> Any:
        """
        A simple decorator to return top contributor data retrieved from GitHub's REST API.
        """

        async def wrapper(self):
            data = await self.get_data()
            return await func(self, data)

        return wrapper

    @get_contributor_before_run
    async def run_tasks(self, contributor: Contributor) -> None:
        """
        Shows the avatar of the top contributor.
        """
        if contributor:
            image = await contributor.generate_image()

            if not global_.TEST_MODE:
                await contributor.post_to_discord()
                await contributor.post_to_twitter()
            else:
                image.show()

        else:
            logging.warning("No contributor for the given time period.")

    @staticmethod
    @aiocron.crontab("0 0 1 * *")
    async def every():
        bot = Bot()
        await bot.run_tasks()

    def run(self) -> None:
        asyncio.get_event_loop().run_forever()
