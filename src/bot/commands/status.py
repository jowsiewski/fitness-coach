import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from src.bot.bot import _get_guild_ids
from src.integrations.intervals_icu.client import IntervalsICUClient, IntervalsICUError
from src.services.fitness_tracker import FitnessTracker

logger = logging.getLogger(__name__)


class StatusCog(commands.Cog):
    """Komendy statusu formy i gotowości."""

    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @discord.slash_command(  # type: ignore[no-untyped-call,untyped-decorator]
        name="status",
        description="💪 Aktualny status formy, gotowość i rekomendacja treningowa",
        guild_ids=_get_guild_ids(),
    )
    async def status(self, ctx: discord.ApplicationContext) -> None:
        """Current form, readiness, recommendation, and today's planned events."""
        await ctx.defer()

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

            async with IntervalsICUClient() as client:
                wellness = await client.get_wellness_today()
                events = await client.get_events(today, tomorrow)

            tracker = FitnessTracker()

            ctl = wellness.get("ctl", 0) or 0
            atl = wellness.get("atl", 0) or 0

            form = tracker.calculate_form(ctl, atl)
            readiness = tracker.assess_readiness(wellness, form)

            # Find today's planned event
            planned_today = None
            for event in events:
                event_date = event.get("start_date_local", "")[:10]
                if event_date == today:
                    planned_today = event
                    break

            recommendation = tracker.training_recommendation(form, readiness, planned_today)

            # Build embed
            tsb = form.get("tsb", 0)
            form_label = form.get("form_label", "—")
            score = readiness.get("readiness_score", 5)

            # Color based on readiness
            if score >= 7:
                color = discord.Color.green()
            elif score >= 4:
                color = discord.Color.gold()
            else:
                color = discord.Color.red()

            embed = discord.Embed(
                title=f"💪 Status formy — {today}",
                description=f"**{form_label}**",
                color=color,
                timestamp=datetime.now(),
            )

            # PMC metrics
            pmc_text = (
                f"```\n"
                f"{'CTL (fitness)':<20} {form.get('ctl', 0):>6.1f}\n"
                f"{'ATL (zmęczenie)':<20} {form.get('atl', 0):>6.1f}\n"
                f"{'TSB (forma)':<20} {tsb:>6.1f}\n"
                f"```"
            )
            embed.add_field(name="📈 Model PMC", value=pmc_text, inline=False)

            # Readiness
            score_bar = "🟩" * int(score) + "⬜" * (10 - int(score))
            embed.add_field(
                name="⚡ Gotowość do treningu",
                value=f"{score_bar} **{score}/10**\n{readiness.get('recommendation', '')}",
                inline=False,
            )

            # Wellness factors
            factors = readiness.get("factors", {})
            wellness_parts = []
            if factors.get("hrv") is not None:
                wellness_parts.append(f"❤️ HRV: **{factors['hrv']}** ms")
            if factors.get("resting_hr") is not None:
                wellness_parts.append(f"💓 Tętno spoczynkowe: **{factors['resting_hr']}** bpm")
            if factors.get("sleep_score") is not None:
                wellness_parts.append(f"😴 Sen: **{factors['sleep_score']}**/100")

            if wellness_parts:
                embed.add_field(
                    name="🩺 Dane wellness",
                    value="\n".join(wellness_parts),
                    inline=False,
                )

            # Today's planned workout
            if planned_today:
                event_name = planned_today.get("name", "Trening")
                event_load = planned_today.get("icu_training_load", 0) or 0
                event_time_s = planned_today.get("moving_time", 0) or 0
                event_time_min = round(event_time_s / 60)
                embed.add_field(
                    name="📋 Zaplanowany trening",
                    value=f"**{event_name}** | TSS ~{event_load} | ~{event_time_min} min",
                    inline=False,
                )

            # Recommendation
            embed.add_field(
                name="🎯 Rekomendacja",
                value=recommendation,
                inline=False,
            )

            embed.set_footer(text="Dane z Intervals.icu + analiza Fitness Coach")

            await ctx.respond(embed=embed)

        except IntervalsICUError as e:
            logger.exception("Intervals.icu API error in /status")
            embed = discord.Embed(
                title="❌ Błąd",
                description=f"Nie udało się pobrać danych z Intervals.icu: {e}",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
        except Exception:
            logger.exception("Unexpected error in /status")
            embed = discord.Embed(
                title="❌ Błąd",
                description="Wystąpił nieoczekiwany błąd. Spróbuj ponownie później.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(StatusCog(bot))
