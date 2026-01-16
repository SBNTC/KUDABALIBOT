from aiogram.fsm.state import State, StatesGroup

class FeedMenuStates(StatesGroup):
    agreement = State()
    main = State()           # Главное меню
    category = State()       # Категория событий
    suggest = State()        # Предложить событие
    ai_chat = State()        # AI чат
    places_menu = State()    # Меню мест
    places_list = State()    # Список мест
    place_detail = State()   # Детали места + отзывы

class AdminSG(StatesGroup):
    list = State()
    view = State()
    edit_category = State()
    edit_date = State()
    edit_summary = State()

class AdminReviewSG(StatesGroup):
    view = State()
    edit_menu = State()
    edit_summary = State()
    edit_date = State()
    edit_category = State()

class AdminCreateSG(StatesGroup):
    summary = State()
    date = State()
    category = State()
