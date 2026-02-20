import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from src.bot.bot import _get_guild_ids
from src.integrations.intervals_icu.client import IntervalsICUClient, IntervalsICUError
from src.services.ai_engine import AIEngine
from src.services.nutrition_planner import NutritionPlanner

logger = logging.getLogger(__name__)


class NutritionCog(commands.Cog):
    """Komendy planowania żywienia."""

    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot

    @discord.slash_command(  # type: ignore[no-untyped-call,untyped-decorator]
        name="nutrition",
        description="🍎 Dzisiejszy plan żywieniowy z makroskładnikami",
        guild_ids=_get_guild_ids(),
    )
    async def nutrition(self, ctx: discord.ApplicationContext) -> None:
        """Today's nutrition plan based on training load."""
        await ctx.defer()

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

            async with IntervalsICUClient() as client:
                wellness = await client.get_wellness_today()
                today_events = await client.get_events(today, today)
                tomorrow_events = await client.get_events(tomorrow, tomorrow)
                today_activities = await client.get_activities(today, today)

            planner = NutritionPlanner()
            weight = wellness.get("weight", 75) or 75
            base_needs = planner.calculate_base_needs(weight)

            # Today's training load (completed or planned)
            today_load = 0.0
            today_duration = 0.0
            if today_activities:
                for a in today_activities:
                    today_load += a.get("icu_training_load", 0) or 0
                    today_duration += (a.get("moving_time", 0) or 0) / 3600
            elif today_events:
                for e in today_events:
                    today_load += e.get("icu_training_load", 0) or 0
                    today_duration += (e.get("moving_time", 0) or 0) / 3600

            # Tomorrow's planned load
            tomorrow_load = sum((e.get("icu_training_load", 0) or 0) for e in tomorrow_events)

            if today_load > 0:
                plan = planner.plan_for_training_day(base_needs, today_load, today_duration)
            else:
                plan = planner.plan_for_rest_day(base_needs)

            # AI-generated detailed plan
            ai = AIEngine()
            ai_plan = await ai.plan_nutrition(weight, today_load, tomorrow_load)

            # Build embed
            day_type = "🏋️ Dzień treningowy" if today_load > 0 else "🛌 Dzień odpoczynku"
            embed = discord.Embed(
                title=f"🍎 Plan żywieniowy — {today}",
                description=f"{day_type} | Waga: **{weight} kg** | TSS: **{today_load:.0f}**",
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )

            # Macros table from calculated plan
            calories = plan.get("calories", 0)
            protein = plan.get("protein_g", 0)
            carbs = plan.get("carbs_g", 0)
            fat = plan.get("fat_g", 0)

            macros_text = (
                f"```\n"
                f"{'Kalorie':<16} {calories:>6} kcal\n"
                f"{'Białko':<16} {protein:>6} g\n"
                f"{'Węglowodany':<16} {carbs:>6} g\n"
                f"{'Tłuszcze':<16} {fat:>6} g\n"
                f"```"
            )
            embed.add_field(name="📊 Makroskładniki (obliczone)", value=macros_text, inline=False)

            # On-bike nutrition if training day
            if today_load > 0:
                carbs_per_h = plan.get("carbs_per_hour_riding", 0)
                hydration = plan.get("hydration_ml", 0)
                ride_info = (
                    f"⚡ Węglowodany: **{carbs_per_h}g/h** | 💧 Nawodnienie: **{hydration} ml**"
                )
                embed.add_field(name="🚴 Na rowerze", value=ride_info, inline=False)

            # AI plan details
            ai_calories = ai_plan.get("calories", 0)
            ai_protein = ai_plan.get("protein_g", 0)
            ai_carbs = ai_plan.get("carbs_g", 0)
            ai_fat = ai_plan.get("fat_g", 0)

            if ai_calories > 0:
                ai_macros = (
                    f"```\n"
                    f"{'Kalorie':<16} {ai_calories:>6} kcal\n"
                    f"{'Białko':<16} {ai_protein:>6} g\n"
                    f"{'Węglowodany':<16} {ai_carbs:>6} g\n"
                    f"{'Tłuszcze':<16} {ai_fat:>6} g\n"
                    f"```"
                )
                embed.add_field(name="🤖 Makroskładniki (AI)", value=ai_macros, inline=False)

            # AI meal suggestions
            pre_ride = ai_plan.get("pre_ride", "")
            during_ride = ai_plan.get("during_ride", "")
            post_ride = ai_plan.get("post_ride", "")
            notes = ai_plan.get("notes", "")

            if pre_ride:
                embed.add_field(name="🍽️ Przed treningiem", value=pre_ride, inline=False)
            if during_ride:
                embed.add_field(name="🚴 Podczas treningu", value=during_ride, inline=False)
            if post_ride:
                embed.add_field(name="💪 Po treningu", value=post_ride, inline=False)
            if notes:
                embed.add_field(name="📝 Uwagi", value=notes, inline=False)

            embed.set_footer(text=f"Plan jutro: TSS ~{tomorrow_load:.0f}")

            await ctx.respond(embed=embed)

        except IntervalsICUError as e:
            logger.exception("Intervals.icu API error in /nutrition")
            embed = discord.Embed(
                title="❌ Błąd",
                description=f"Nie udało się pobrać danych z Intervals.icu: {e}",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
        except Exception:
            logger.exception("Unexpected error in /nutrition")
            embed = discord.Embed(
                title="❌ Błąd",
                description="Wystąpił nieoczekiwany błąd. Spróbuj ponownie później.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(NutritionCog(bot))
