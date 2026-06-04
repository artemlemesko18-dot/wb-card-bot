from aiogram.fsm.state import State, StatesGroup


class FSMGeneration(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_photo = State()
    waiting_for_description = State()
    confirmation = State()


class FSMAdmin(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_crystals_amount = State()
    waiting_for_broadcast_text = State()
    waiting_for_setting_value = State()
