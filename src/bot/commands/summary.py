import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from src.bot.bot import _get_guild_ids
from src.integrations.intervals_icu.client import IntervalsICUClient, IntervalsICUError
from src.services.activity_analyzer import ActivityAnalyzer
from src.services.ai_engine import AIEngine

logger = logging.getLogger(__name__)


class SummaryCog(commands.Cog):
    """Komendy podsumowań treningowych."""

    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @discord.slash_command(  # type: ignore[no-untyped-call,untyped-decorator]
        name="summary",
        description="🚴 Podsumowanie ostatniego treningu z analizą AI",
        guild_ids=_get_guild_ids(),
    )
    async def summary(self, ctx: discord.ApplicationContext) -> None:
        """Fetch the latest activity, analyze it, and present an AI summary."""
        await ctx.defer()

        try:
            newest = datetime.now().strftime("%Y-%m-%d")
            oldest = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            async with IntervalsICUClient() as client:
                activities = await client.get_activities(oldest, newest)

            if not activities:
                embed = discord.Embed(
                    title="🚴 Podsumowanie treningu",
                    description="Brak aktywności w ostatnich 7 dniach.",
                    color=discord.Color.orange(),
                )
                await ctx.respond(embed=embed)
                return

            last_activity = activities[0]

            analyzer = ActivityAnalyzer()
            analysis = analyzer.analyze(last_activity)

            ai = AIEngine()
            ai_summary = await ai.summarize_activity(last_activity)

            embed = discord.Embed(
                title=f"🚴 {analysis.get('name', 'Trening')}",
                description=ai_summary,
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            date_str = analysis.get("date", "")[:10] if analysis.get("date") else "—"
            embed.add_field(name="📅 Data", value=date_str, inline=True)
            embed.add_field(
                name="⏱️ Czas",
                value=f"{analysis.get('duration_min', 0)} min",
                inline=True,
            )
            embed.add_field(
                name="📏 Dystans",
                value=f"{analysis.get('distance_km', 0)} km",
                inline=True,
            )

            embed.add_field(
                name="⚡ Średnia moc",
                value=f"{analysis.get('avg_power', 0)} W",
                inline=True,
            )
            embed.add_field(
                name="💪 NP",
                value=f"{analysis.get('normalized_power', 0)} W",
                inline=True,
            )
            embed.add_field(
                name="🏋️ TSS",
                value=f"{analysis.get('tss', 0)}",
                inline=True,
            )

            embed.add_field(
                name="❤️ Tętno śr./max",
                value=f"{analysis.get('avg_hr', 0)} / {analysis.get('max_hr', 0)} bpm",
                inline=True,
            )
            embed.add_field(
                name="🔥 Kalorie",
                value=f"{analysis.get('calories', 0)} kcal",
                inline=True,
            )
            embed.add_field(
                name="🏔️ Przewyższenie",
                value=f"{analysis.get('elevation_m', 0)} m",
                inline=True,
            )

            zone = analysis.get("power_zone", "N/A")
            embed.set_footer(
                text=f"Strefa mocy: {zone} | IF: {analysis.get('intensity_factor', 0)}"
            )

            await ctx.respond(embed=embed)

        except IntervalsICUError as e:
            logger.exception("Intervals.icu API error in /summary")
            embed = discord.Embed(
                title="❌ Błąd",
                description=f"Nie udało się pobrać danych z Intervals.icu: {e}",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
        except Exception:
            logger.exception("Unexpected error in /summary")
            embed = discord.Embed(
                title="❌ Błąd",
                description="Wystąpił nieoczekiwany błąd. Spróbuj ponownie później.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    @discord.slash_command(  # type: ignore[no-untyped-call,untyped-decorator]
        name="week",
        description="📊 Tygodniowe podsumowanie treningów z oceną AI",
        guild_ids=_get_guild_ids(),
    )
    async def week(self, ctx: discord.ApplicationContext) -> None:
        """Weekly summary with aggregated stats and AI assessment."""
        await ctx.defer()

        try:
            newest = datetime.now().strftime("%Y-%m-%d")
            oldest = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            future = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

            async with IntervalsICUClient() as client:
                activities = await client.get_activities(oldest, newest)
                wellness = await client.get_wellness(oldest, newest)
                planned = await client.get_events(newest, future)

            if not activities:
                embed = discord.Embed(
                    title="📊 Podsumowanie tygodnia",
                    description="Brak aktywności w ostatnim tygodniu.",
                    color=discord.Color.orange(),
                )
                await ctx.respond(embed=embed)
                return

            analyzer = ActivityAnalyzer()
            weekly = analyzer.weekly_summary(activities)

            ai = AIEngine()
            assessment = await ai.assess_fitness(activities, wellness, planned)

            embed = discord.Embed(
                title="📊 Podsumowanie tygodnia",
                description=assessment,
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            embed.add_field(
                name="🚴 Treningi",
                value=f"{weekly.get('activity_count', 0)} treningów / {weekly.get('rest_days', 0)} dni odpoczynku",
                inline=False,
            )

            embed.add_field(
                name="⏱️ Łączny czas",
                value=f"{weekly.get('total_hours', 0)} h",
                inline=True,
            )
            embed.add_field(
                name="📏 Łączny dystans",
                value=f"{weekly.get('total_km', 0)} km",
                inline=True,
            )
            embed.add_field(
                name="🏋️ Łączny TSS",
                value=f"{weekly.get('total_tss', 0)}",
                inline=True,
            )

            embed.add_field(
                name="🏔️ Przewyższenie",
                value=f"{weekly.get('total_elevation_m', 0)} m",
                inline=True,
            )
            embed.add_field(
                name="🔥 Kalorie",
                value=f"{weekly.get('total_calories', 0)} kcal",
                inline=True,
            )
            embed.add_field(
                name="⚡ Śr. IF",
                value=f"{weekly.get('avg_intensity_factor', 0)}",
                inline=True,
            )

            embed.set_footer(text=f"Okres: {oldest} — {newest}")

            await ctx.respond(embed=embed)

        except IntervalsICUError as e:
            logger.exception("Intervals.icu API error in /week")
            embed = discord.Embed(
                title="❌ Błąd",
                description=f"Nie udało się pobrać danych z Intervals.icu: {e}",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
        except Exception:
            logger.exception("Unexpected error in /week")
            embed = discord.Embed(
                title="❌ Błąd",
                description="Wystąpił nieoczekiwany błąd. Spróbuj ponownie później.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(SummaryCog(bot))
