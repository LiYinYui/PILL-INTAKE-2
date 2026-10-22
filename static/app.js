// Этот файл отвечает за меню и отправку запросов без перезагрузки страницы.
// Все данные и правила работы с препаратами по-прежнему обрабатываются в Python.

const burgerButton = document.getElementById("burgerBtn");
const navigation = document.getElementById("nav");

// Открываем и закрываем мобильное меню.
if (burgerButton && navigation) {
    burgerButton.addEventListener("click", function () {
        burgerButton.classList.toggle("active");
        navigation.classList.toggle("active");

        const menuIsOpen = navigation.classList.contains("active");
        burgerButton.setAttribute("aria-expanded", menuIsOpen ? "true" : "false");
    });

    // После выбора ссылки закрываем меню на маленьком экране.
    navigation.addEventListener("click", function (event) {
        if (event.target.closest("a")) {
            burgerButton.classList.remove("active");
            navigation.classList.remove("active");
            burgerButton.setAttribute("aria-expanded", "false");
        }
    });
}

// Преобразуем HTML, который вернул Flask, в документ для чтения отдельных блоков.
function parsePage(html) {
    return new DOMParser().parseFromString(html, "text/html");
}

// Обновляем только те части страницы, которые изменились.
// Весь документ не перезагружается, поэтому положение прокрутки не прыгает наверх.
function updatePage(newPage) {
    // Обновляем список препаратов и счётчики.
    const currentList = document.getElementById("medicationList");
    const nextList = newPage.getElementById("medicationList");

    if (currentList && nextList) {
        currentList.innerHTML = nextList.innerHTML;
    }

    // Показываем новое сообщение от Python или убираем старое.
    const currentMessages = document.querySelector(".messages");
    const nextMessages = newPage.querySelector(".messages");

    if (currentMessages && nextMessages) {
        currentMessages.replaceWith(nextMessages);
    } else if (currentMessages && !nextMessages) {
        currentMessages.remove();
    } else if (!currentMessages && nextMessages) {
        const heading = document.querySelector(".maintextcontainer");
        if (heading) {
            heading.insertAdjacentElement("afterend", nextMessages);
        }
    }

    // Обновляем тему, не перезагружая страницу.
    const nextTheme = newPage.documentElement.getAttribute("data-theme");
    if (nextTheme) {
        document.documentElement.setAttribute("data-theme", nextTheme);
    }

    const currentThemeButton = document.getElementById("themeToggleBtn");
    const nextThemeButton = newPage.getElementById("themeToggleBtn");
    if (currentThemeButton && nextThemeButton) {
        currentThemeButton.innerHTML = nextThemeButton.innerHTML;
    }

    // Обновляем информационное окно, если пользователь его открыл или закрыл.
    const currentModal = document.getElementById("infoModal");
    const nextModal = newPage.getElementById("infoModal");
    if (currentModal && nextModal) {
        currentModal.replaceWith(nextModal);
    }
}

// Запрашиваем обновлённую страницу у Flask, но не заменяем весь экран.
async function requestPage(url, options = {}) {
    const response = await fetch(url, options);

    if (!response.ok) {
        throw new Error("Сервер вернул ошибку: " + response.status);
    }

    const html = await response.text();
    const newPage = parsePage(html);
    updatePage(newPage);

    return response;
}

// Обрабатываем все формы отправки данных через запрос, чтобы сайт не перезагружался.
// Обработчик стоит на document, поэтому работает и для карточек, добавленных позднее.
document.addEventListener("submit", async function (event) {
    const form = event.target.closest('form[method="post" i]');
    if (!form) return;

    event.preventDefault();

    // Не даём случайно отправить одну и ту же форму несколько раз подряд.
    const submitButton = event.submitter || form.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;

    try {
        await requestPage(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        // После добавления очищаем оба поля ввода.
        if (form.classList.contains("input-section")) {
            form.reset();
        }
    } catch (error) {
        console.error("Не удалось выполнить действие:", error);
        alert("Не удалось связаться с приложением. Проверь, что сервер Python запущен.");
    } finally {
        // Кнопка могла быть заменена обновлением списка — проверяем старый элемент.
        if (submitButton && submitButton.isConnected) submitButton.disabled = false;
    }
});

// Открываем справку без полной перезагрузки страницы.
document.addEventListener("click", async function (event) {
    const link = event.target.closest("a.info-pill-btn, a.modal-close-btn");
    if (!link) return;

    event.preventDefault();

    try {
        const response = await requestPage(link.href);
        // Сохраняем открытие/закрытие справки в истории браузера.
        history.pushState({}, "", response.url);
    } catch (error) {
        console.error("Не удалось открыть справку:", error);
        alert("Не удалось загрузить информацию. Проверь, что сервер Python запущен.");
    }
});

// Кнопки «Назад» и «Вперёд» в браузере тоже обновляют только нужные блоки.
window.addEventListener("popstate", async function () {
    try {
        await requestPage(window.location.href);
    } catch (error) {
        console.error("Не удалось восстановить страницу:", error);
    }
});

// В полночь обновляем страницу, чтобы Python начал новый день приёмов.
// Если сайт закрыт в это время, счётчики сбросятся при следующем открытии.
function refreshAtMidnight() {
    const now = new Date();
    const midnight = new Date(now);
    midnight.setHours(24, 0, 0, 0);
    const millisecondsUntilMidnight = midnight.getTime() - now.getTime();

    setTimeout(function () {
        location.reload();
    }, millisecondsUntilMidnight + 1000);
}

refreshAtMidnight();
