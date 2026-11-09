from aiogram import Router

from app.bot.handlers import admin, user


def get_routers() -> list[Router]:
    """Order matters: admin commands first, generic fallbacks last."""
    return [admin.router, user.router]
