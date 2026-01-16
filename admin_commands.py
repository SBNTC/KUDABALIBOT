# Добавить в admin_router

@admin_router.message(Command("clean"))
async def cmd_clean_old(message: Message):
    """Удалить устаревшие события из review"""
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            delete(ScrapedEvent)
            .where(ScrapedEvent.status == "review")
            .where(ScrapedEvent.event_date < date.today())
        )
        await session.commit()
        await message.answer(f"🗑 Удалено {result.rowcount} устаревших событий")
