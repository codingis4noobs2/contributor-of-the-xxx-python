# Imports.
import random
from io import BytesIO
from typing import Dict

import aiohttp
from discord_webhook import DiscordWebhook
from PIL import Image, ImageDraw, ImageFont
from twitter import OAuth, Twitter

from src import secrets

from .organization import Organization


# Class for top contributors.
class Contributor:
    """
    Represents the top contributor of a GitHub Organization.
    """

    def __init__(
        self,
        data: Dict,
        organization: Organization,
        pr_count: int = 0,
        issue_count: int = 0,
    ) -> None:
        self.login = data["login"]
        self.avatar_url = data["avatar_url"]
        self.bio = data["bio"]
        self.twitter_username = data["twitter_username"]
        self.pr_count = pr_count
        self.issue_count = issue_count
        self.organization = organization
        self.image_bytes: bytes = None

    def __str__(self) -> str:
        return f"Top contributor of {self.org}: {self.login} | {self.html_url}"

    @staticmethod
    def get_quote() -> str:
        """
        Returns a fancy tech quote :P
        """
        # short quotes about technology
        quotes = [
            "Technology is best when it brings people together.",
            "Talk is cheap, show me the code",
            "It is only when they go wrong that machines remind you how powerful they are.",
            "Data! Data Data! I can't make bricks without clay!",
            "Without data you're just another person with an opinion.",
            "If the statistics are boring, you've got the wrong numbers.",
            "Data is a precious thing and will last longer than the systems themselves.",
            "Errors using inadequate data are much less than those using no data at all.",
            "It's not a faith in technology. It's faith in people.",
            "I have not failed. I've just found 10,000 ways that won't work.",
            "Technology like art is a soaring exercise of the human imagination.",
            "Innovation is the outcome of a habit, not a random act.",
            "Any sufficiently advanced technology is indistinguishable from magic.",
            "It's not that we use technology, we live technology.",
            "You affect the world by what you browse.",
            "What new technology does is create new opportunities to do a job that customers want done.",
            "Let's go invent tomorrow instead of worrying about what happened yesterday.",
            "The great growling engine of change - technology.",
            "Computers are useless. They can only give you answers.",
            "The human spirit must prevail over technology",
            "Books don't need batteries.",
            "The production of too many useful things results in too many useless people",
            "Technology is a useful servant but a dangerous master.",
            "Technology like art is a soaring exercise of the human imagination",
            "Any sufficiently advanced technology is equivalent to magic.",
            "Any technology distinguishable from magic is insufficiently advanced",
            "I might love my e-reader, but I'd never pass up the chance to browse real books.",
            "'User' is the word used by the computer professional when they mean 'idiot.'",
            "What did people do when they went to the bathroom before smartphones?",
            "We are stuck with technology when what we really want is just stuff that works.",
        ]
        return random.choice(quotes)

    async def generate_image(self) -> Image:
        """
        Generates the banner image for the top contributor.
        """

        image = Image.open("assets/background.png") if self.issue_count else Image.open("assets/no_issues_background.png")

        async with aiohttp.ClientSession() as session:
            async with session.get(self.avatar_url) as response:
                avatar = Image.open(BytesIO(await response.read())).resize((200, 200))
                image.paste(avatar, (500, 270))

            async with session.get(self.organization.avatar_url) as response:
                org_avatar = Image.open(BytesIO(await response.read())).resize(((80, 80) if self.issue_count else (160, 160)))

                bigsize = (org_avatar.size[0] * 3, org_avatar.size[1] * 3)
                mask = Image.new("L", bigsize, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0) + bigsize, fill=255)
                mask = mask.resize(org_avatar.size, Image.ANTIALIAS)
                org_avatar.putalpha(mask)

                image.paste(org_avatar, ((60, 28) if self.issue_count else (123, 146)), org_avatar.convert("RGBA"))

        draw = ImageDraw.Draw(image)

        draw.text(
            xy=((image.width / 2), 165),
            text=self.contributor_of_the(),
            fill=(255, 255, 255),
            font=ImageFont.truetype("assets/fonts/JosefinSansT.ttf", 28),
            anchor="mm",
        )

        draw.text(
            xy=((image.width / 2), 210),
            text=self.login,
            fill=(255, 255, 255),
            font=ImageFont.truetype("assets/fonts/JosefinSansSB.ttf", 40),
            anchor="mm",
        )

        if self.bio:
            draw.text(
                xy=((image.width / 2), 540),
                text=self.bio[:37] + "..." if len(self.bio) > 50 else self.bio,
                fill=(255, 255, 255),
                font=ImageFont.truetype("assets/fonts/JosefinSansEL.ttf", 30),
                anchor="mm",
            )

        draw.text(
            xy=((image.width / 2), 640),
            text=self.get_quote(),
            fill=(255, 255, 255),
            font=ImageFont.truetype("assets/fonts/JosefinSansTI.ttf", 21),
            anchor="mm",
        )

        if self.issue_count:
            draw.text(
                xy=(200, 280),
                text=str(self.issue_count),
                fill=(183, 183, 183),
                font=ImageFont.truetype("assets/fonts/JosefinSansSB.ttf", 120),
                anchor="ma",
            )

        draw.text(
            xy=(1000, 280),
            text=str(self.pr_count),
            fill=(183, 183, 183),
            font=ImageFont.truetype("assets/fonts/JosefinSansSB.ttf", 120),
            anchor="ma",
        )

        draw.text(
            xy=((150, 50) if self.issue_count else (130, 350)),
            text=f"@{self.organization.login.lower()}",
            fill=(255, 255, 255),
            font=ImageFont.truetype("assets/fonts/JosefinSansT.ttf", 30),
        )

        overlay = Image.open("assets/overlay.png") if self.issue_count else Image.open("assets/no_issues_overlay.png")
        image = Image.alpha_composite(image, overlay)

        buffer = BytesIO()
        image.save(buffer, format="png")
        self.image_bytes = buffer.getvalue()

        return image

    def contributor_of_the(self) -> str:
        message = "Contributor of the "

        match (secrets.time_period_days):
            case 1:
                message += "Day"
            case 7:
                message += "Week"
            case 30:
                message += "Month"
            case _:
                message += f"last {secrets.time_period_days} Days"

        return message

    async def post_to_discord(self) -> None:
        """
        Posts contributor result image to Discord.
        """
        caption = f"The top {self.contributor_of_the().lower()} is " + f"`{self.login}` with {self.pr_count} merged prs"
        if self.issue_count > 0:
            caption += f" and {self.issue_count} opened issues"
        caption += "."
        webhook = DiscordWebhook(
            url=secrets.discord_hook,
            content=caption,
        )
        webhook.add_file(file=self.image_bytes, filename="contributor.png")
        webhook.execute()

    async def post_to_twitter(self) -> None:
        """
        Posts contributor result image to Twitter.
        """

        auth = OAuth(
            secrets.twitter_access_token,
            secrets.twitter_access_secret,
            secrets.twitter_key,
            secrets.twitter_secret,
        )

        twit = Twitter(auth=auth)
        t_upload = Twitter(domain="upload.twitter.com", auth=auth)
        id_img1 = t_upload.media.upload(media=self.image_bytes)["media_id_string"]
        status = (
            f"The top {self.contributor_of_the().lower()} is "
            + f"{f'@{self.twitter_username}' if self.twitter_username is not None else self.login}"
            + f" with {self.pr_count} merged prs"
        )
        if self.issue_count > 0:
            status += f" and {self.issue_count} opened issues"
        status += "."

        twit.statuses.update(
            status=status,
            media_ids=",".join([id_img1]),
        )
