"""My-pills — простой дневник приёма лекарств на Python и Flask.

Основные действия (добавление, счётчик, сброс, удаление и сохранение)
выполняются на Python. Страница оформлена HTML-шаблоном и оригинальным CSS.
"""

import json
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from datetime import date
# Flask будет искать HTML-шаблоны в папке templates.
app = Flask(__name__)
# Ключ нужен Flask для хранения выбранной темы в сессии браузера.
# Для локального учебного проекта такого ключа достаточно.
app.secret_key = "my-pills-local-project-key"

# BASE_DIR — папка, в которой находится этот файл app.py.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "medications.json"

# База краткой справочной информации. Это общие сведения, а не назначение лечения.
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

# Кнопки быстрого добавления: название, ключ справки и число приёмов в день.
# Эти значения задают только счётчик в приложении, а не медицинскую дозировку.
QUICK_ADD = [
    {"key": "vitamin_d", "name": "Витамин D", "daily_count": 1},
    {"key": "vitamin_c", "name": "Витамин C", "daily_count": 1},
    {"key": "omega_3", "name": "Омега-3", "daily_count": 2},
    {"key": "magnesium", "name": "Магний", "daily_count": 1},
    {"key": "vitamin_b", "name": "Комплекс витаминов B", "daily_count": 1},
    {"key": "iron", "name": "Железо", "daily_count": 1},
]

# Словарь помогает быстро находить нужные варианты по ключу или названию.
INFO_KEY_BY_NAME = {item["name"]: key for key, item in PILL_INFO.items()}
QUICK_ADD_BY_KEY = {item["key"]: item for item in QUICK_ADD}
LAST_DAY_FILE = DATA_DIR / "last_day.txt"


def save_medications(medications):
    """Сохраняет список препаратов в файл."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(medications, file, ensure_ascii=False, indent=4)


def load_medications():
    """Загружает препараты и сбрасывает счётчики, если наступил новый день."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Если файла ещё нет, начинаем с пустого списка.
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                medications = json.load(file)
        except (json.JSONDecodeError, OSError):
            medications = []
    else:
        medications = []

    today = date.today().isoformat()  # Например, 2026-10-22.

    # Запоминаем день последнего открытия приложения.
    if LAST_DAY_FILE.exists():
        last_day = LAST_DAY_FILE.read_text(encoding="utf-8").strip()
    else:
        last_day = today

    # Если дата поменялась, начинаем дневной счёт заново.
    if last_day != today:
        for medicine in medications:
            medicine["current_count"] = 0
        save_medications(medications)
        LAST_DAY_FILE.write_text(today, encoding="utf-8")
    elif not LAST_DAY_FILE.exists():
        LAST_DAY_FILE.write_text(today, encoding="utf-8")

    return medications


def add_medicine(name, daily_count, info_key=None):
    """Создаёт запись о новом препарате."""
    medications = load_medications()
    new_id = max([medicine.get("id", 0) for medicine in medications], default=0) + 1

    if info_key is None:
        info_key = INFO_KEY_BY_NAME.get(name)

    medications.append({
        "id": new_id,
        "name": name,
        "daily_count": daily_count,
        "current_count": 0,
        "info_key": info_key,
    })
    save_medications(medications)


def home():
    """Открывает главную страницу."""
    return redirect(url_for("index"))


@app.get("/")
def index():
    medications = load_medications()
    info_key = request.args.get("info", "")
    return render_template(
        "index.html",
        medications=medications,
        quick_add=QUICK_ADD,
        info=PILL_INFO.get(info_key),
        info_key=info_key,
        theme=session.get("theme", "light"),
    )


@app.post("/add")
def add_medication():
    """Добавляет препарат из формы на странице."""
    name = request.form.get("name", "").strip()

    try:
        daily_count = int(request.form.get("daily_count", "0"))
    except ValueError:
        daily_count = 0

    if not name or daily_count < 1:
        flash("Введите название препарата и число приёмов от 1 и выше.", "error")
        return home()

    add_medicine(name, daily_count)
    flash(f"Препарат «{name}» добавлен.", "success")
    return home()


@app.post("/quick-add/<key>")
def quick_add_medication(key):
    """Добавляет препарат по кнопке быстрого добавления."""
    medicine = QUICK_ADD_BY_KEY.get(key)
    if medicine is None:
        flash("Такого варианта быстрого добавления нет.", "error")
        return home()

    add_medicine(medicine["name"], medicine["daily_count"], medicine["key"])
    flash(f"Препарат «{medicine['name']}» добавлен.", "success")
    return home()


@app.post("/medication/<int:medicine_id>/<action>")
def medication_action(medicine_id, action):
    """Отмечает приём, сбрасывает счётчик или удаляет препарат."""
    medications = load_medications()
    medicine = next((item for item in medications if item.get("id") == medicine_id), None)

    if medicine is None:
        flash("Препарат не найден.", "error")
        return home()

    if action == "take":
        if medicine["current_count"] < medicine["daily_count"]:
            medicine["current_count"] += 1
            flash(f"Отмечен приём: «{medicine['name']}».", "success")
        else:
            flash("Все приёмы на сегодня уже отмечены.", "error")
    elif action == "reset":
        medicine["current_count"] = 0
        flash(f"Счётчик препарата «{medicine['name']}» сброшен.", "success")
    elif action == "delete":
        medications = [item for item in medications if item.get("id") != medicine_id]
        flash(f"Препарат «{medicine['name']}» удалён.", "success")
    else:
        flash("Неизвестное действие.", "error")

    save_medications(medications)
    return home()


@app.post("/theme")
def toggle_theme():
    """Меняет светлую тему на тёмную и обратно."""
    session["theme"] = "dark" if session.get("theme", "light") == "light" else "light"
    return home()


if __name__ == "__main__":
    # Запускаем сайт на своём компьютере.
    app.run(host="127.0.0.1", port=5000, debug=False)
