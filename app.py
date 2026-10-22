import json
from datetime import date
from pathlib import Path
from flask import Flask, flash, redirect, render_template, request, session, url_for

# --- Настройки приложения ---
app = Flask(__name__)  # Создаю приложение Flask.
app.secret_key = "my-pills-local-project-key"  # Нужно для сохранения темы в сессии.

# Получаю пути к папкам и файлам, чтобы не писать их вручную.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "medications.json"
LAST_DAY_FILE = DATA_DIR / "last_day.txt"  # Здесь запоминается дата последнего сброса.


# --- Справочная информация ---
# По ключу программа находит название и описание препарата.
PILL_INFO = {
    "vitamin_d": {
        "name": "Витамин D",
        "time": "Следуйте назначению врача или инструкции к препарату.",
        "advice": (
            "Подходящая дозировка зависит от возраста, состояния здоровья и других факторов. "
            "Не подбирайте дозу только по общим советам."
        ),
        "description": (
            "Витамин D помогает организму усваивать кальций и важен для здоровья костей."
        ),
    },
    "vitamin_c": {
        "name": "Витамин C",
        "time": "Следуйте инструкции к препарату.",
        "advice": (
            "У некоторых людей приём натощак может вызывать дискомфорт в желудке. "
            "Проверьте инструкцию и учитывайте рекомендации врача."
        ),
        "description": (
            "Витамин C участвует в работе иммунной системы, синтезе коллагена и усвоении железа."
        ),
    },
    "omega_3": {
        "name": "Омега-3",
        "time": "Следуйте инструкции к конкретному препарату.",
        "advice": (
            "Состав и дозировка у разных добавок отличаются. Если вы принимаете другие лекарства, "
            "обсудите совместимость с врачом или фармацевтом."
        ),
        "description": (
            "Омега-3 — группа жирных кислот, которые участвуют в работе организма."
        ),
    },
    "magnesium": {
        "name": "Магний",
        "time": "Следуйте назначению врача или инструкции.",
        "advice": (
            "Не превышайте указанную дозировку. Добавки магния могут взаимодействовать "
            "с некоторыми лекарствами."
        ),
        "description": (
            "Магний участвует в работе мышц, нервной системы и многих обменных процессов."
        ),
    },
    "vitamin_b": {
        "name": "Комплекс витаминов B",
        "time": "Следуйте инструкции к конкретному комплексу.",
        "advice": (
            "Состав комплексов различается. Проверьте количество каждого витамина и не "
            "сочетайте несколько добавок без необходимости."
        ),
        "description": (
            "Витамины группы B участвуют в обмене веществ и нормальной работе нервной системы."
        ),
    },
    "iron": {
        "name": "Железо",
        "time": "Принимайте в соответствии с назначением врача.",
        "advice": (
            "Железо следует принимать при наличии показаний: избыток может быть опасен. "
            "Уточните у врача, как сочетать препарат с едой и другими лекарствами."
        ),
        "description": (
            "Железо необходимо для образования гемоглобина, который переносит кислород в крови."
        ),
    },
}


# --- Готовые варианты быстрого добавления ---
# daily_count — число отметок в приложении за день, а не дозировка лекарства.
QUICK_ADD = [
    {"key": "vitamin_d", "name": "Витамин D", "daily_count": 1},
    {"key": "vitamin_c", "name": "Витамин C", "daily_count": 1},
    {"key": "omega_3", "name": "Омега-3", "daily_count": 2},
    {"key": "magnesium", "name": "Магний", "daily_count": 1},
    {"key": "vitamin_b", "name": "Комплекс витаминов B", "daily_count": 1},
    {"key": "iron", "name": "Железо", "daily_count": 1},
]


# --- Сохранение и загрузка препаратов ---
def save_medications(medications):
    """Сохраняет список препаратов в JSON-файл."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)  # Создаю папку, если её ещё нет.
    with DATA_FILE.open("w", encoding="utf-8") as file:
        # Записываю список в файл, чтобы данные не пропали после закрытия сайта.
        json.dump(medications, file, ensure_ascii=False, indent=4)


def load_medications():
    """Загружает препараты и проверяет, не наступил ли новый день."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Если файл существует, читаю список из него.
    # Если файл повреждён или его не удалось прочитать, начинаю с пустого списка.
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                medications = json.load(file)
        except (json.JSONDecodeError, OSError):
            medications = []
    else:
        medications = []

    today = date.today().isoformat()  # Например, "2026-10-22".

    # Читаю дату прошлой проверки.
    if LAST_DAY_FILE.exists():
        last_day = LAST_DAY_FILE.read_text(encoding="utf-8").strip()
    else:
        last_day = today

    # Если дата изменилась, обнуляю отметки, но оставляю сами препараты.
    if last_day != today:
        for medicine in medications:
            medicine["current_count"] = 0

        save_medications(medications)
        LAST_DAY_FILE.write_text(today, encoding="utf-8")
    elif not LAST_DAY_FILE.exists():
        LAST_DAY_FILE.write_text(today, encoding="utf-8")

    return medications  # Возвращаю список той функции, которая его запросила.


def add_medicine(name, daily_count, info_key=None):
    """Добавляет препарат, если такого названия ещё нет."""
    name = name.strip()  # Убираю пробелы в начале и конце названия.
    medications = load_medications()

    # Проверяю, не добавляли ли такое название раньше.
    # lower() позволяет не учитывать заглавные и строчные буквы.
    for medicine in medications:
        if medicine["name"].strip().lower() == name.lower():
            return False  # False означает, что препарат уже есть.

    # Нахожу следующий свободный ID, чтобы не перепутать карточки.
    new_id = 1
    for medicine in medications:
        if medicine.get("id", 0) >= new_id:
            new_id = medicine.get("id", 0) + 1

    # Если ключ справки не передали, ищу его по названию.
    if info_key is None:
        for key, item in PILL_INFO.items():
            if item["name"].lower() == name.lower():
                info_key = key
                break

    # Создаю новую карточку. Счётчик начинается с нуля.
    medications.append({
        "id": new_id,
        "name": name,
        "daily_count": daily_count,
        "current_count": 0,
        "info_key": info_key,
    })

    save_medications(medications)
    return True  # True означает, что препарат добавлен.


def home():
    # Эта функция нужна, чтобы после действия возвращаться на главную страницу.
    return redirect(url_for("index"))


# --- Главная страница ---
@app.get("/")
def index():
    medications = load_medications()
    info_key = request.args.get("info", "")  # Читаю ключ справки из адреса страницы.

    # Передаю HTML-шаблону данные, которые нужно показать.
    return render_template(
        "index.html",
        medications=medications,
        quick_add=QUICK_ADD,
        info=PILL_INFO.get(info_key),
        info_key=info_key,
        theme=session.get("theme", "light"),  # По умолчанию тема светлая.
    )


# --- Добавление через форму ---
@app.post("/add")
def add_medication():
    name = request.form.get("name", "").strip()  # Получаю название из формы.

    try:
        daily_count = int(request.form.get("daily_count", "0"))  # Превращаю значение в число.
    except ValueError:
        daily_count = 0  # Если введено не число, считаю его неправильным.

    if not name or daily_count < 1:
        flash("Введите название препарата и число приёмов от 1 и выше.", "error")
        return home()

    # Если такой препарат уже есть, показываю сообщение и ничего не добавляю.
    if not add_medicine(name, daily_count):
        flash(f"Препарат «{name}» уже есть в списке.", "error")
        return home()

    flash(f"Препарат «{name}» добавлен.", "success")
    return home()


# --- Быстрое добавление ---
@app.post("/quick-add/<key>")
def quick_add_medication(key):
    # Ищу выбранный вариант в списке готовых препаратов.
    # Эта проверка нужна на случай, если придёт неправильный запрос.
    medicine = None
    for item in QUICK_ADD:
        if item["key"] == key:
            medicine = item
            break

    if medicine is None:
        flash("Такого варианта быстрого добавления нет.", "error")
        return home()

    # Запрещаю добавить препарат, если такое название уже есть.
    if not add_medicine(medicine["name"], medicine["daily_count"], medicine["key"]):
        flash(f"Препарат «{medicine['name']}» уже есть в списке.", "error")
        return home()

    flash(f"Препарат «{medicine['name']}» добавлен.", "success")
    return home()


# --- Приём, сброс или удаление ---
@app.post("/medication/<int:medicine_id>/<action>")
def medication_action(medicine_id, action):
    medications = load_medications()

    # Ищу препарат по ID. Если не найду, medicine останется None.
    medicine = None
    for item in medications:
        if item.get("id") == medicine_id:
            medicine = item
            break

    if medicine is None:
        flash("Препарат не найден.", "error")
        return home()

    if action == "take":
        # Не даю счётчику превысить заданное число приёмов.
        # В HTML кнопка отключается после достижения лимита.
        if medicine["current_count"] < medicine["daily_count"]:
            medicine["current_count"] += 1
            flash(f"Отмечен приём: «{medicine['name']}».", "success")

    elif action == "reset":
        medicine["current_count"] = 0
        flash(f"Счётчик препарата «{medicine['name']}» сброшен.", "success")

    elif action == "delete":
        # Создаю новый список без удаляемого препарата.
        new_medications = []
        for item in medications:
            if item.get("id") != medicine_id:
                new_medications.append(item)

        medications = new_medications
        flash(f"Препарат «{medicine['name']}» удалён.", "success")

    else:
        # Защита от неизвестного действия в запросе.
        flash("Неизвестное действие.", "error")
        return home()

    save_medications(medications)
    return home()


# --- Переключение темы ---
@app.post("/theme")
def toggle_theme():
    # Если тема светлая, переключаю на тёмную, иначе — обратно.
    if session.get("theme", "light") == "light":
        session["theme"] = "dark"
    else:
        session["theme"] = "light"

    return home()
