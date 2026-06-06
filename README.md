# ♚ Шахматы — веб-приложение на Flask

Шахматная доска с drag-and-drop, двумя режимами игры и авторизацией по имени (без пароля).

## Возможности

- **Игра с ботом** — случайные легальные ходы
- **Игра с человеком** — hot-seat (одна клавиатура), выбор соперника из списка
- **Авторизация** — только username, если пользователя нет — создаётся автоматически
- **Drag-and-drop** — доска через chessboard.js + chess.js, ходы без перезагрузки
- **Сдаться** — кнопка завершает партию победой соперника
- **История** — таблица последних 10 игр на главной
- **Тёмная тема** — Bootstrap 5, минимум стилей

## Технологии

- **Flask** + flask-sqlalchemy + flask-session
- **python-chess** — серверная валидация ходов
- **chessboard.js** + **chess.js** — клиентская отрисовка и drag-and-drop
- **SQLite** — хранение пользователей и игр

## Установка и запуск

```bash
pip install -r requirements.txt
python app.py
```

Открой `http://127.0.0.1:5000`, введи любое имя и играй.

## Структура

```
├── app.py              # маршруты, логика игры, бот
├── models.py           # User и Game (SQLAlchemy)
├── requirements.txt
├── static/
│   ├── style.css
│   └── img/chesspieces/wikipedia/   # картинки фигур
└── templates/
    ├── base.html
    ├── login.html
    ├── index.html
    ├── game.html
    └── lobby.html
```
