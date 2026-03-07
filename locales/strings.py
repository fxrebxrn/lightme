TEXTS = {
    'uk': {
        'select_lang': '<tg-emoji emoji-id="5253604305704854338">🇺🇦</tg-emoji> Будь ласка, оберіть мову:',
        'lang_set': '<tg-emoji emoji-id="5253604305704854338">🇺🇦</tg-emoji> Мову встановлено: Українська',
        'sub_recommend': '<tg-emoji emoji-id="5771868281212245617">📢</tg-emoji> <b>Рекомендуємо підписатися!</b>\nЩоб бути в курсі новин, підпишіться на наш канал.',
        'sub_btn': 'Підписатись',
        'continue_btn': 'Продовжити ➡️',
        'menu_main': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> Головне меню:',
        'btn_add_queue': '➕ Додати чергу',
        'btn_my_queues': '📁 Мої черги',
        'my_que': '<tg-emoji emoji-id="5452165780579843515">📁</tg-emoji> Збережені черги:',
        'btn_schedules': '📅 Графіки',
        'btn_support': '💬 Зв`язок',
        'btn_status': '⌛️ Статус',
        'btn_settings': '⚙️ Налаштування',
        'choose_comp': '<tg-emoji emoji-id="5967816500415827773">💻</tg-emoji> Оберіть компанію:',
        'choose_queue': '<tg-emoji emoji-id="5257963315258204021">🏘</tg-emoji> Оберіть чергу для <b>{company}</b>:',
        'schedule_view': '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> <b>Графік {company} {queue} на {date}:</b>\n\n{schedule}\n\n<tg-emoji emoji-id="5407078373547582630">💡</tg-emoji> <b>Зі світлом:</b> {total_light}\n<tg-emoji emoji-id="5404500130449599239">💡</tg-emoji> <b>Без світла:</b> {total_no_light}\n\n<i>Оновлено: {updated}</i>\n\n<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot">Монітор світла</a>',
        'no_schedule': '❗️ На жаль, графік для цієї черги на обрану дату ще не завантажено.',
        'schedule_view_no_totals': '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> <b>Графік {company} {queue} на {date}:</b>\n\n{schedule}\n\n<i>Оновлено: {updated}</i>\n\n<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot">Монітор світла</a>',
        'back': '⬅️ Назад',
        'limit_error': '❗️ Максимум 5 черг! Видаліть щось.',
        'added': '✅ Підписано: {company} {queue}',
        'exists': '✅ Ви підписані.',
        'deleted': '✅ Видалено',
        'empty_list': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Список підписок порожній.',
        'support_text': '<tg-emoji emoji-id="5988023995125993550">🛠</tg-emoji> <b>Підтримка:</b> {user}\n<tg-emoji emoji-id="5987880246865565644">💰</tg-emoji> <b>Донат:</b> {url}\n<tg-emoji emoji-id="5771868281212245617">📢</tg-emoji> <b>Наш канал (FAQ, тех. підтримка)</b>: https://t.me/lightmetech',
        'tech_work': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> <b>Технічні роботи</b>\nБот тимчасово недоступний. Спробуйте пізніше.\nСлідкуйте за новинами бота на нашому каналі @lightmetech',
        'settings_text': '<tg-emoji emoji-id="5258096772776991776">⚙</tg-emoji> Налаштування:',
        'btn_lang_switch': '🇺🇦/🇷🇺 Змінити мову',
        'reminder_off': '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Нагадування: очікуване вимкнення світла в черзі {company} {queue} через 10 хв.',
        'reminder_on': '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Нагадування: очікуване ввімкнення світла в черзі {company} {queue} через 10 хв.',
        
        # --- НОВІ ПОВІДОМЛЕННЯ ---
        'off_now': '<tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji> Світло ВИМКНЕНО в черзі {company} {queue}.', # Для сумісності
        'on_now': '<tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji> Світло УВІМКНЕНО в черзі {company} {queue}.',   # Для сумісності
        
        'off_now_extended': '<tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji> Світло <b>ВИМКНЕНО</b> в черзі {company} {queue} | <i>{time}</i>.\n\n<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Наступне ввімкнення о {next_time} <i>(Через {duration})</i>.',
        'on_now_extended': '<tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji> Світло <b>УВІМКНЕНО</b> в черзі {company} {queue} | <i>{time}</i>.\n\n<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Наступне вимкнення о {next_time} <i>(Через {duration})</i>.',
        
        'units_hours': 'год.', # або 'години', універсально для повідомлень
        'units_minutes': 'хв.',
        # -------------------------

        'btn_notifications': '🔔 Сповіщення',
        'notifications_text': 'Налаштування сповіщень:',
        'notif_label_off': 'Сповіщення про вимкнення',
        'notif_label_on': 'Сповіщення про ввімкнення',
        'notif_label_off_10': 'Нагадування за 10 хв до вимкнення',
        'notif_label_on_10': 'Нагадування за 10 хв до ввімкнення',
        'btn_toggle_all': '⚡ Увімкнути/Вимкнути всі сповіщення',
        'notif_all_set': 'Усі сповіщення встановлені на: {state}',
        'today_label': 'Сьогодні',
        'tomorrow_label': 'Завтра',
        'btn_compare': '⚡ Спільне світло',
        'btn_compare_new': '➕ Нове порівняння',
        'btn_compare_my': '📚 Мої порівняння',
        'status_choose_queue': '<tg-emoji emoji-id="5257963315258204021">🏘</tg-emoji> Оберіть чергу для перегляду статусу:',
        'status_title': '<tg-emoji emoji-id="5891211339170326418">⌛️</tg-emoji> <b>Статус по {company} {queue}:</b>',
        'status_now_on': '<tg-emoji emoji-id="5280863578369311403">🟢</tg-emoji> <b>ЗАРАЗ СВІТЛО Є</b>',
        'status_now_off': '<tg-emoji emoji-id="5280474686260527507">🔴</tg-emoji> <b>ЗАРАЗ СВІТЛА НЕМАЄ</b>',
        'status_to_off': '<tg-emoji emoji-id="5258258882022612173">⏲</tg-emoji> <b>До вимкнення:</b> {duration} (о {time})',
        'status_to_on': '<tg-emoji emoji-id="5258258882022612173">⏲</tg-emoji> <b>До ввімкнення:</b> {duration} (о {time})',
        'status_next_off': '<tg-emoji emoji-id="5891100675042974129">📅</tg-emoji> <b>Наступна подія:</b> <tg-emoji emoji-id="5330017696660599813">🔲</tg-emoji> Відключення о {off_time} до {on_time}.',
        'status_next_on': '<tg-emoji emoji-id="5891100675042974129">📅</tg-emoji> <b>Наступна подія:</b> <tg-emoji emoji-id="5330396907913098490">🟩</tg-emoji> Включення о {on_time}.',
        'status_no_data': '<tg-emoji emoji-id="5879813604068298387">❗️</tg-emoji> <b>Немає актуального графіка для цієї черги.</b>',
        'status_refresh': '🔄 Оновити',
        'status_back': '⬅️ Назад',
        'status_monitoring': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot">Монітор світла</a>',
        'status_hours_short': 'год.',
        'status_minutes_short': 'хв.',
        'status_less_minute': '< 1 хв.',
        'cmp_menu_text': '<tg-emoji emoji-id="5843553939672274145">⚡️</tg-emoji> Оберіть дію для порівняння черг:',
        'cmp_choose_first': '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> Оберіть першу компанію для порівняння:',
        'cmp_choose_second': '<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> Оберіть другу компанію для порівняння:',
        'cmp_ready_preview': '<tg-emoji emoji-id="5258391025281408576">📈</tg-emoji> Пара для порівняння:\n{comp1} {queue1}  +  {comp2} {queue2}\n🔩 Оберіть дату або збережіть цю пару.',
        'cmp_save_button': '💾 Зберегти порівняння',
        'cmp_saved_ok': '<tg-emoji emoji-id="5260341314095947411">👀</tg-emoji> Пара збережена.',
        'cmp_saved_msg': '<tg-emoji emoji-id="5260341314095947411">👀</tg-emoji> Збережено: {name}',
        'cmp_saved_fail': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Не вдалося зберегти.',
        'cmp_list_header': '<tg-emoji emoji-id="5877316724830768997">🗃</tg-emoji> Ваші збережені порівняння:',
        'cmp_no_saved': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> У вас немає збережених порівнянь.',
        'cmp_deleted_ok': '<tg-emoji emoji-id="5260341314095947411">👀</tg-emoji> Порівняння видалено.',
        'cmp_choose_first': '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> Оберіть першу чергу для порівняння:',
        'cmp_choose_second': '<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> Оберіть другу чергу для порівняння:',
        'cmp_result_header': '<tg-emoji emoji-id="5258216851472654189">💡</tg-emoji> Спільне ввімкнення для {comp1} {queue1} та {comp2} {queue2} на {date}:',
        'cmp_no_common': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Спільних інтервалів увімкнення для {comp1} {queue1} та {comp2} {queue2} на {date} не знайдено.',
        'cmp_error_restart': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Помилка стану. Будь ласка, перезапустіть вибір: натисніть ще раз Нова порівняння.',
        'cmp_details_button': '🗓 Графікі',
        'cmp_details_header': '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> Ввімкнення {comp1} {queue1} та {comp2} {queue2} на {date}:',
        'cmp_original_1': '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> {comp} {queue}:',
        'cmp_original_2': '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> {comp} {queue}:',
        'toggle_day_label': '👀 Переглянути: {day}',
        'no_schedule_short': '<tg-emoji emoji-id="5258503720928288433">ℹ️</tg-emoji> На жаль, графік для цієї черги на обрану дату ще не завантажено.',
        'cmp_delete_saved': '❌ Видалити порівняння',
        'cmp_no_data': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> На жаль, графік на черги ще не завантажено.',
        'cmp_limit_reached': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Ви досягли ліміту збережених порівнянь 5/5. Видаліть старі, щоб зберегти нову.',
        'no_outages': '<tg-emoji emoji-id="5021905410089550576">✅</tg-emoji> <b>Світло не вимикатимуть!</b>',
        'schedule_hours_value': '{value} год.',
        'schedule_view_no_data': '<tg-emoji emoji-id=\"5258105663359294787\">🗓</tg-emoji> <b>Графік {company} {queue} на {date}:</b>\n\n{schedule}',
       
        'status_light_until': '<tg-emoji emoji-id="5280863578369311403">🟢</tg-emoji> <b>Статус:</b> світло є до <b>{time}</b> <i>(ще {remain})</i>',
        'status_no_light_until': '<tg-emoji emoji-id="5280863578369311403">🔴</tg-emoji> <b>Статус:</b> світла немає до <b>{time}</b> <i>(ще {remain})</i>',
        'status_light_now': '<tg-emoji emoji-id="5280863578369311403">🟢</tg-emoji> <b>Статус:</b> світло є',
        'section_outages': '<tg-emoji emoji-id="5978809241576673582">✅</tg-emoji> <b>Відключення:</b>',
        'section_stats': '<tg-emoji emoji-id="5875291072225087249">📊</tg-emoji> <b>Статистика:</b>',
        'stats_light': '<tg-emoji emoji-id="5845677551892042113">⚡️</tg-emoji> <b>Зі світлом:</b> {value}',
        'stats_no_light': '<tg-emoji emoji-id="5258084811293102719">⚡️</tg-emoji> <b>Без світла:</b> {value}',
        'monitor_link': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot"><b>Монітор світла</b></a>',
        'schedule_not_loaded':
        '<tg-emoji emoji-id="6019102674832595118">⚠️</tg-emoji> На жаль, графік для цієї черги на обрану дату ще не завантажено.',
        'no_outages_today': '<tg-emoji emoji-id="5021905410089550576">✅</tg-emoji> <b>Світло не вимикатимуть!</b>',
        'updated': '<tg-emoji emoji-id="5900104897885376843">🕓</tg-emoji> Оновлення',
        'schedule_title': '<b>Графік {company} {queue} на {date}</b>',

        'update_notify': '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> <b>Оновлення графіку {company} {queue} на {date}:</b>',
        'notify_outages_title': '<tg-emoji emoji-id="5978809241576673582">✅</tg-emoji> <b>Відключення:</b>',
        'notify_stats_title': '<tg-emoji emoji-id="5875291072225087249">📊</tg-emoji> <b>Статистика:</b>',
        'notify_on_label': '<tg-emoji emoji-id="5845677551892042113">⚡️</tg-emoji> <b>Зі світлом:</b>',
        'notify_off_label': '<tg-emoji emoji-id="5258084811293102719">⚡️</tg-emoji> <b>Без світла:</b>',
        'monitor_link': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot"><b>Монітор світла</b></a>',
        'hour_short_dot': 'год.',

        'avar_warning': '<tg-emoji emoji-id="6030563507299160824">❗️</tg-emoji> Зараз діють аварійні відключення, графік може не діяти!',
    },
    'ru': {
        'select_lang': '<tg-emoji emoji-id="5449408995691341691">🇷🇺</tg-emoji> Пожалуйста, выберите язык:',
        'lang_set': '<tg-emoji emoji-id="5449408995691341691">🇷🇺</tg-emoji> Язык установлен: Русский',
        'sub_recommend': '<tg-emoji emoji-id="5771868281212245617">📢</tg-emoji> <b>Рекомендуем подписаться!</b>\nЧтобы быть в курсе новостей, подпишитесь на наш канал.',
        'sub_btn': 'Подписаться',
        'continue_btn': 'Продолжить ➡️',
        'menu_main': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> Главное меню:',
        'btn_add_queue': '➕ Добавить очередь',
        'btn_my_queues': '📁 Мои очереди',
        'my_que': '<tg-emoji emoji-id="5452165780579843515">📁</tg-emoji> Сохраненные очереди:',
        'btn_schedules': '📅 Графики',
        'btn_support': '💬 Связь',
        'btn_status': '⌛️ Статус',
        'btn_settings': '⚙️ Настройки',
        'choose_comp': '<tg-emoji emoji-id="5967816500415827773">💻</tg-emoji> Выберите компанию:',
        'choose_queue': '<tg-emoji emoji-id="5257963315258204021">🏘</tg-emoji> Выберите очередь для <b>{company}</b>:',
        'schedule_view': '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> <b>График {company} {queue} на {date}:</b>\n\n{schedule}\n\n<tg-emoji emoji-id="5407078373547582630">💡</tg-emoji> <b>Со светом:</b> {total_light}\n<tg-emoji emoji-id="5404500130449599239">💡</tg-emoji> <b>Без света:</b> {total_no_light}\n\n<i>Обновлено: {updated}</i>\n\n<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot">Монитор света</a>',
        'no_schedule': '❗️ К сожалению, график для этой очереди на выбранную дату еще не загружен.',
        'schedule_view_no_totals': '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> <b>График {company} {queue} на {date}:</b>\n\n{schedule}\n\n<i>Обновлено: {updated}</i>\n\n<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot">Монитор света</a>',
        'back': '⬅️ Назад',
        'limit_error': '❗️ Максимум 5 очередей! Удалите что-то.',
        'added': '✅ Подписано: {company} {queue}',
        'exists': '✅ Вы подписаны.',
        'deleted': '✅ Удалено',
        'empty_list': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Список подписок пуст.',
        'support_text': '<tg-emoji emoji-id="5988023995125993550">🛠</tg-emoji> <b>Поддержка:</b> {user}\n<tg-emoji emoji-id="5987880246865565644">💰</tg-emoji> <b>Донат:</b> {url}\n<tg-emoji emoji-id="5771868281212245617">📢</tg-emoji> <b>Наш канал (FAQ, тех. поддержка)</b>: https://t.me/lightmetech',
        'tech_work': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> <b>Технические работы</b>\nБот временно недоступен. Попробуйте позже.\nСледите за обновлениями бота на нашем канале @lightmetech',
        'settings_text': '<tg-emoji emoji-id="5258096772776991776">⚙</tg-emoji> Настройки:',
        'btn_lang_switch': '🇺🇦/🇷🇺 Сменить язык',
        'reminder_off': '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Напоминание: ожидаемое отключение света в очереди {company} {queue} через 10 минут.',
        'reminder_on': '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Напоминание: ожидаемое включение света в очереди {company} {queue} через 10 минут.',
        
        # --- НОВЫЕ СООБЩЕНИЯ ---
        'off_now': '<tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji> Свет ОТКЛЮЧЁН в очереди {company} {queue}.',
        'on_now': '<tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji> Свет ВКЛЮЧЁН в очереди {company} {queue}.',
        
        'off_now_extended': '<tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji> Свет <b>ОТКЛЮЧЁН</b> в очереди {company} {queue} | <i>{time}</i>.\n\n<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Следующее включение в {next_time} <i>(Через {duration})</i>.',
        'on_now_extended': '<tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji> Свет <b>ВКЛЮЧЁН</b> в очереди {company} {queue} | <i>{time}</i>.\n\n<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> Следующее отключение в {next_time} <i>(Через {duration})</i>.',

        'units_hours': 'ч.', # или 'часа'
        'units_minutes': 'мин.',
        # -----------------------

        'btn_notifications': '🔔 Уведомления',
        'notifications_text': 'Настройки уведомлений:',
        'notif_label_off': 'Уведомления об отключении',
        'notif_label_on': 'Уведомления о включении',
        'notif_label_off_10': 'Напоминание за 10 мин до отключения',
        'notif_label_on_10': 'Напоминание за 10 мин до включения',
        'btn_toggle_all': '⚡ Включить/Выключить все уведомления',
        'notif_all_set': 'Все уведомления установлены на: {state}',
        'today_label': 'Сегодня',
        'tomorrow_label': 'Завтра',
        'btn_compare': '⚡ Совместный свет',
        'btn_compare_new': '➕ Новое сравнение',
        'btn_compare_my': '📚 Мои сравнения',
        'status_choose_queue': '<tg-emoji emoji-id="5257963315258204021">🏘</tg-emoji> Выберите очередь для просмотра статуса:',
        'status_title': '<tg-emoji emoji-id="5891211339170326418">⌛️</tg-emoji> <b>Статус по {company} {queue}:</b>',
        'status_now_on': '<tg-emoji emoji-id="5280863578369311403">🟢</tg-emoji> <b>СЕЙЧАС СВЕТ ЕСТЬ</b>',
        'status_now_off': '<tg-emoji emoji-id="5280474686260527507">🔴</tg-emoji> <b>СЕЙЧАС СВЕТА НЕТ</b>',
        'status_to_off': '<tg-emoji emoji-id="5258258882022612173">⏲</tg-emoji> <b>До отключения:</b> {duration} (в {time})',
        'status_to_on': '<tg-emoji emoji-id="5258258882022612173">⏲</tg-emoji> <b>До включения:</b> {duration} (в {time})',
        'status_next_off': '<tg-emoji emoji-id="5891100675042974129">📅</tg-emoji> <b>Следующее событие:</b> <tg-emoji emoji-id="5330017696660599813">🔲</tg-emoji> Отключение в {off_time} до {on_time}.',
        'status_next_on': '<tg-emoji emoji-id="5891100675042974129">📅</tg-emoji> <b>Следующее событие:</b> <tg-emoji emoji-id="5330396907913098490">🟩</tg-emoji> Включение в {on_time} до.',
        'status_no_data': '<tg-emoji emoji-id="5879813604068298387">❗️</tg-emoji> <b>Нет актуального графика для этой очереди.</b>',
        'status_refresh': '🔄 Обновить',
        'status_back': '⬅️ Назад',
        'status_monitoring': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot">Монитор света</a>',
        'status_hours_short': 'ч.',
        'status_minutes_short': 'мин.',
        'status_less_minute': '< 1 мин.',
        'cmp_menu_text': '<tg-emoji emoji-id="5843553939672274145">⚡️</tg-emoji> Выберите действие для сравнения очередей:',
        'cmp_choose_first': '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> Выберите первую компанию для сравнения:',
        'cmp_choose_second': '<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> Выберите вторую компанию для сравнения:',
        'cmp_ready_preview': '<tg-emoji emoji-id="5258391025281408576">📈</tg-emoji> Пара для сравнения:\n{comp1} {queue1}  +  {comp2} {queue2}\n🔩 Выберите дату или сохраните эту пару.',
        'cmp_save_button': '💾 Сохранить сравнение',
        'cmp_saved_ok': '<tg-emoji emoji-id="5260341314095947411">👀</tg-emoji> Пара сохранена.',
        'cmp_saved_msg': '<tg-emoji emoji-id="5260341314095947411">👀</tg-emoji> Сохранено: {name}',
        'cmp_saved_fail': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Не удалось сохранить.',
        'cmp_list_header': '<tg-emoji emoji-id="5877316724830768997">🗃</tg-emoji> Ваши сохраненные сравнения:',
        'cmp_no_saved': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> У вас нет сохраненных сравнений.',
        'cmp_deleted_ok': '<tg-emoji emoji-id="5260341314095947411">👀</tg-emoji> Сравнение удалено.',
        'cmp_choose_first': '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> Выберите первую очередь для сравнения:',
        'cmp_choose_second': '<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> Выберите вторую очередь для сравнения:',
        'cmp_result_header': '<tg-emoji emoji-id="5258216851472654189">💡</tg-emoji> Совместное включение для {comp1} {queue1} и {comp2} {queue2} на {date}:',
        'cmp_no_common': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Совместных интервалов включения для {comp1} {queue1} и {comp2} {queue2} на {date} не найдено.',
        'cmp_error_restart': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Ошибка состояния. Пожалуйста, перезапустите выбор: нажмите еще раз Новое сравнение.',
        'cmp_details_button': '🗓 Графики',
        'cmp_details_header': '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> Включения {comp1} {queue1} и {comp2} {queue2} на {date}:',
        'cmp_original_1': '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> {comp} {queue}:',
        'cmp_original_2': '<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> {comp} {queue}:',
        'toggle_day_label': '👀 Посмотреть: {day}',
        'no_schedule_short': '<tg-emoji emoji-id="5258503720928288433">ℹ️</tg-emoji> К сожалению, график для этой очереди на выбранную дату еще не загружен.',
        'cmp_delete_saved': '❌ Удалить сравнение',
        'cmp_no_data': '<tg-emoji emoji-id="5258503720928288433">ℹ️</tg-emoji> К сожелению, график на очереди еще не загружен.',
        'cmp_limit_reached': '<tg-emoji emoji-id="5258474669769497337">❗️</tg-emoji> Вы достигли лимита сохранённых сравнений 5/5. Удалите старые, чтобы сохранить новое.',
        'no_outages': '<tg-emoji emoji-id="5021905410089550576">✅</tg-emoji> <b>Свет не будут выключать!</b>',
        'schedule_hours_value': '{value} ч.',
        'schedule_view_no_data': '<tg-emoji emoji-id=\"5258105663359294787\">🗓</tg-emoji> <b>График {company} {queue} на {date}:</b>\n\n{schedule}',

        'status_light_until': '<tg-emoji emoji-id="5280863578369311403">🟢</tg-emoji> <b>Статус:</b> свет есть до <b>{time}</b> <i>(ещё {remain})</i>',
        'status_no_light_until': '<tg-emoji emoji-id="5280474686260527507">🔴</tg-emoji> <b>Статус:</b> света нет до <b>{time}</b> <i>(ещё {remain})</i>',
        'status_light_now': '<tg-emoji emoji-id="5280863578369311403">🟢</tg-emoji> <b>Статус:</b> света нет',
        'section_outages': '<tg-emoji emoji-id="5978809241576673582">✅</tg-emoji> <b>Отключения:</b>',
        'section_stats': '<tg-emoji emoji-id="5875291072225087249">📊</tg-emoji> <b>Статистика:</b>',
        'stats_light': '<tg-emoji emoji-id="5845677551892042113">⚡️</tg-emoji> <b>Со светом:</b> {value}',
        'stats_no_light': '<tg-emoji emoji-id="5258084811293102719">⚡️</tg-emoji> <b>Без света:</b> {value}',
        'monitor_link': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot"><b>Монитор света</b></a>',
        'schedule_not_loaded':
        '<tg-emoji emoji-id="6019102674832595118">⚠️</tg-emoji> К сожелению, график на эту очередь еще не загружен.',
        'no_outages_today': '<tg-emoji emoji-id="5021905410089550576">✅</tg-emoji> <b>Свет не будут выключать!</b>',
        'updated': '<tg-emoji emoji-id="5900104897885376843">🕓</tg-emoji> Обновление',
        'schedule_title': '<b>График {company} {queue} на {date}</b>',

        'update_notify': '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> <b>Обновление графика {company} {queue} на {date}:</b>',
        'notify_outages_title': '<tg-emoji emoji-id="5978809241576673582">✅</tg-emoji> <b>Отключения:</b>',
        'notify_stats_title': '<tg-emoji emoji-id="5875291072225087249">📊</tg-emoji> <b>Статистика:</b>',
        'notify_on_label': '<tg-emoji emoji-id="5845677551892042113">⚡️</tg-emoji> <b>Со светом:</b>',
        'notify_off_label': '<tg-emoji emoji-id="5258084811293102719">⚡️</tg-emoji> <b>Без света:</b>',
        'monitor_link': '<tg-emoji emoji-id="5280504819751101776">🤩</tg-emoji> <a href="https://t.me/lightmeuaBot"><b>Монитор света</b></a>',
        'hour_short_dot': 'ч.',

        'avar_warning': '<tg-emoji emoji-id="6030563507299160824">❗️</tg-emoji> Сейчас действуют аварийные отключения, график может не действовать!',
    }
}

def get_text(lang_code, key, **kwargs):
    lang = lang_code if lang_code in TEXTS else 'uk'
    return TEXTS[lang].get(key, key).format(**kwargs)

































