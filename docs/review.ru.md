# Инструкция для проверки хакатона

## Комплект поставки

- GitHub: https://github.com/Ulitkad/info-arena-hackathon
- Docker Hub: https://hub.docker.com/r/ulitkad/info-arena
- Образ: **`ulitkad/info-arena:latest`**, Linux `amd64` и `arm64`.
- Файлы запуска: **`compose.yml` и `.env.example`**.

Один контейнер включает frontend, Nginx, FastAPI, планировщик и MAX-бота.
Отдельно запускать backend или бота не нужно. На сервере достаточно Docker Engine
и Docker Compose v2 с поддержкой `up --wait` (Compose 2.20+), интернета и свободного
порта `8080`. Python, Node.js, Git и компиляторы не нужны. Команды ниже — Bash/Linux;
`openssl` генерирует секрет, `curl` скачивает файлы и проверяет HTTP.

| Режим | Что проверяется | Что дополнительно нужно |
| --- | --- | --- |
| Локальное демо | Все роли и бизнес-сценарии в браузере | Ничего; MAX-токен и HTTPS не нужны |
| Реальный MAX | Старт бота, кнопка Mini App, подписанный вход и приглашения | Свой MAX-бот, токен, MAX ID администратора, публичный HTTPS-адрес |

## A. Локальное демо без MAX

Создайте **новый отдельный каталог** и скачайте `compose.yml` и `.env.example`
из репозитория командами ниже. Не используйте каталог/volumes production-развёртывания. Дополнительные
`compose.override.*`, сертификаты и исходники для этого режима не нужны.

```bash
mkdir info-arena-demo
cd info-arena-demo
curl --fail --location --output compose.yml \
  https://raw.githubusercontent.com/Ulitkad/info-arena-hackathon/main/compose.yml
curl --fail --location --output .env.example \
  https://raw.githubusercontent.com/Ulitkad/info-arena-hackathon/main/.env.example

cp .env.example .env
sed -i "s/replace-with-at-least-32-random-characters/$(openssl rand -hex 32)/" .env
sed -i \
  -e 's/^DEV_AUTH=false$/DEV_AUTH=true/' \
  -e 's/^SEED_DEMO=false$/SEED_DEMO=true/' \
  .env
chmod 600 .env
docker compose config --quiet
docker compose pull
docker compose up -d --wait --wait-timeout 180
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
```

Ожидается один контейнер `app` со статусом `healthy`, ответ API `{"status":"ok"}`.
Откройте **http://localhost:8080**. Внизу страницы выберите демороль и нажмите
«Открыть арену». Пароли не нужны. Для смены роли выйдите через шапку приложения.
`BOT_TOKEN` оставьте пустым: `bot is disabled` в логах здесь нормально.
Это проверка Mini App.

Для Docker на удалённом сервере `localhost` браузера не указывает на сервер.
Не открывайте демовход в интернет. Создайте SSH-туннель с вашего компьютера:

```bash
ssh -N -L 8080:127.0.0.1:8080 user@server
```

Откройте http://localhost:8080 на своём компьютере. При занятом порте измените
`WEB_PORT` и `BASE_APP_URL` в `.env`, используйте новый порт в командах и туннеле.

## B. Реальный MAX-бот

Используйте **другой каталог** с чистыми volumes, не базу демо. Скачайте файлы
из репозитория (команды выполняются из родительского каталога, не внутри демо):

```bash
mkdir info-arena-max
cd info-arena-max
curl --fail --location --output compose.yml \
  https://raw.githubusercontent.com/Ulitkad/info-arena-hackathon/main/compose.yml
curl --fail --location --output .env.example \
  https://raw.githubusercontent.com/Ulitkad/info-arena-hackathon/main/.env.example
```

1. Создайте/выберите бота в [MAX для бизнеса](https://business.max.ru/).
   Получите токен, имя из `https://max.ru/<имя>` и числовой MAX ID человека,
   который станет первым администратором. Это ID человека, не бота.
2. Скопируйте `.env.example` в `.env`, сгенерируйте `SECRET_KEY` через
   `openssl rand -hex 32` и заполните настройки. Ниже только заглушки:

   ```dotenv
   BOT_TOKEN=YOUR_NEW_MAX_BOT_TOKEN
   BOT_USERNAME=YOUR_BOT_NAME_WITHOUT_AT
   ADMIN_MAX_ID=YOUR_NUMERIC_MAX_USER_ID
   SECRET_KEY=YOUR_RANDOM_SECRET_AT_LEAST_32_CHARACTERS
   BASE_APP_URL=https://arena.example.org
   WEB_PORT=8080
   WEB_BIND_ADDRESS=127.0.0.1
   DEV_AUTH=false
   SEED_DEMO=false
   MAX_CA_BUNDLE=
   ```

   Остальные строки оставьте как в шаблоне. Токены команды не нужны: используйте
   свой бот и секрет. `MAX_CA_BUNDLE` обычно пуст: образ содержит публичный CA MAX.
3. Настройте внешний HTTPS reverse proxy и тот же URL Mini App в кабинете MAX.
   Нужен корректный сертификат и WebSocket `/ws`. Внутри контейнера порт **8080**,
   протокол **HTTP**. Встроенный Nginx не выпускает HTTPS-сертификаты.
4. Используется **long polling**: нужен исходящий HTTPS к
   `platform-api2.max.ru:443`, webhook endpoint не нужен. Не запускайте другой
   polling-процесс с тем же токеном. Старую webhook-подписку удаляйте через MAX API
   только после решения перейти на polling; приложение не удаляет её само.
5. Запустите и проверьте:

   ```bash
   chmod 600 .env
   docker compose pull
   docker compose up -d --wait --wait-timeout 180
   docker compose exec app python -m app.bot_check
   docker compose logs --since=5m -f app
   ```

   Диагностика должна подтвердить токен и отсутствие webhooks. Она не читает
   очередь событий, не отправляет сообщения и не меняет подписки.
6. Откройте **своего** бота в MAX, нажмите «Старт» или отправьте `/start`.
   Ожидается приветствие и кнопка «Открыть арену». Откройте Mini App через неё,
   а не обычную вкладку: реальному входу нужен подписанный MAX `initData`.
   Человек из `ADMIN_MAX_ID` после проверенного входа получает роль администратора.
   Остальные новые пользователи ожидают назначения.
7. Администратор создаёт учреждение и приглашение управляющего. Управляющий
   принимает приглашение, создаёт группы/предметы, назначает преподавателей,
   приглашает учеников. Подробнее: [Подключение MAX](../README.ru.md#подключение-max).

### Как подключить HTTPS-прокси

**Прокси на самом хосте:** оставьте loopback-привязку. Пример для установленного
на хосте Caddy (это инфраструктура сервера, не часть образа):

```caddyfile
arena.example.org {
    reverse_proxy 127.0.0.1:8080
}
```

**Прокси в Docker:** его `127.0.0.1` не указывает на приложение. Добавьте в основной
`compose.yml` следующие поля, **сохраняя** остальные поля сервиса и volumes:

```yaml
services:
  app:
    networks:
      proxy:
        aliases:
          - info-arena

networks:
  proxy:
    external: true
    name: YOUR_EXISTING_PROXY_NETWORK
```

Оба контейнера должны быть в этой существующей сети. Upstream Caddy —
`info-arena:8080`, не `info-arena:<WEB_PORT>`. Имя сети зависит от инфраструктуры
организаторов. Объявление сети только внизу без `services.app.networks` не
подключает сервис. Блок `ports` можно удалить или оставить на `127.0.0.1`.
`0.0.0.0` открывает порт на всех IPv4-интерфейсах — это не требуется для общей сети.

Проверка: `curl --fail https://arena.example.org/api/health`.
Штатное приложение требует только двух файлов; HTTPS-прокси и сертификат домена
предоставляет инфраструктура сервера. Дополнительный CA mount для MAX не нужен.
