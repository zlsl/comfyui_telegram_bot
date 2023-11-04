# ComfyUI telegram bot

## Telegram-бот для интеграции ComfyUI

Работают text2image, image2image. Есть поддержка LoRA. Через IPAdapter работает замена лиц, стилизация

Бот для теста: @stablecats_bot

## Установка и настройка

Необходима рабочая установка ComfyUI с дополнительными модулями:

- ComfyUI-Impact-Pack
- ComfyUI_UltimateSDUpscale

Необходима также установка моделей для сегментации: *face_yolov8m.pt*

Апскейлер: *4xNMKDSuperscale_4xNMKDSuperscale.pt*

ControlNet модель: *control_v11f1e_sd15_tile.pth*

Файл default_lora.safetensors из каталога assets необходимо скопировать в ваш каталог LoRA. Это workaround для workflow без LoRA.


Переименовать файл config.yaml.samlpe в config.yaml и настроить под себя:
```
network:
  BOT_TOKEN: 'xxx:xxxxxx' - токен telegram бота
  SERVER_ADDRESS: "127.0.0.1:8188" - адрес API ComfyUI

bot:
  TRANSLATE: True - Переводить ли языки промпта на английский (через deep_translate)
  DENY_MESSAGE: "Access denied" - Сообщение, если пользователь не в белом списке
  HELP_TEXT: "Для генерации можно использовать текст на русском языке
По-умолчанию каритнка создаётся в разрешении 512x512 пикселей
В промпте можно указать размер ШИРИНАхВЫСОТА. Например - 1024x512.
Команды:
/upscale .... - создаст картинку высокого разрешения
/face .... - исправит дефекты лиц"

comfyui:
  DEFAULT_MODEL: 'revAnimatedFp16_122.safetensors' - имя модели по-умолчанию
  DEFAULT_VAE: 'vaeFtMse840000Ema_v10.safetensors' - имя VAE модели по-умолчанию
  DEFAULT_CONTROLNET: 'control_v11f1e_sd15_tile.pth' - модель ControlNet для image2image
  SAMPLER: 'uni_pc' - используемый сэмплер
  SAMPLER_STEPS: 30 - количество шагов денойса
  MAX_STEPS: 100
  TOKEN_MERGE_RATIO: '0.6'
  CLIP_SKIP: '-1'
  CONTROLNET_STRENGTH: '0.9'
  DEFAULT_WIDTH: 512
  DEFAULT_HEIGHT: 512
  MAX_WIDTH: 2048 - ограничение ширины     
  MAX_HEIGHT: 2048 - ограничение высоты
  BEAUTIFY_PROMPT: ',masterpiece, perfect, small details, highly detailed, best, high quality, professional photo' - добавляется к промпту
  NEGATIVE_PROMPT: 'low quality, worst quality, embedding:badhandv4, blurred, deformed, embedding:EasyNegative, embedding:badquality, watermark, text, font, signage, artist name, text, caption, jpeg artifacts' - настройте под свои нужды негативный промпт
```

## Описание работы

Используются workflow для генерации, в каталоги workflows они находятся в формате ComfyUI API

По-умолчанию при получении чистого промпта генерируется картинка с размерами DEFAULT_WIDTHxDEFAULT_HEIGHT, размер можно указывать в формате WIDTHxHEIGHT

Ответом от бота будут два сообщения: картинка (с потерей качетсва из-за сжатия телеграмом) и PNG файл с исходным качеством.

Если боту отправить картинку, то картинка будет преобразована, согласно промпту, в данном случае команды `/face`, `/upscale` также работают. Важно! Для img2img использутеся COntrolNet, а не классический денойс,что позволяет дать максимально приближенный к оригиналу результат.

Для добавления своего негативного промпта вместо встроенного - можно добавить к сообщению через разделитель `|`

Пример полного промпта (image2image) с отправкой референсной картинки:

`@rev #vlozhkin:0.4 $0.6 %50 768x512 /face pretty woman in red|blurred, bad quality`

- `@rev` - выбор модели (revAnimated)
- `#vlozhkin:0.4` - установка LoRA с силой 0.4
- `$0.6` - коэффициент ControlNet (0 - нет, 1 - максимум)
- `%50` - 50 шаков сэмплера
- `768x512` - разрешение на входе
- `/face` - улучшение лиц и апсекйл
- `pretty woman in red` - позитивный промпт
- `|` - разделитель промптов
- `blurred, bad quality` - негативный промпт

## Дополнительные команды

`%50` - указать количество шагов сэмплера

`$0.5` - strength для image2image controlnet модели

`/models` - список моделей

`/loras` - список доступных LoRA



Исходная картинка | Результат
--- | ---
![Исходная картинка](https://raw.githubusercontent.com/zlsl/comfyui_telegram_bot/main/examples/i2i_src.jpg) | ![Исходная картинка](https://raw.githubusercontent.com/zlsl/comfyui_telegram_bot/main/examples/i2i_result.jpg) Милый демон с белой змеиной чешуёй, изумрудные глаза, острые когти 1024x1024


В каталоге upload сохраняются картинки отправленные боту

Каталог generated - результаты генераций


## Команды

`/start`, `/help` - информация об использовании из HELP_TEXT

`/upscale` - апскейл готовой картинки

`/face` - коррекциея лиц (каждое лицо на картинке увеличит время генерации)

`/me` - установка фото лица (пустая команда для очистки), можно указать вес лица добавив его к команде. Например /me 0.7

`/style` - установка картинки для стилизации (пустая команда для очистки), можно указать вес cnbkz добавив его к команде. Например /style 0.7

## Ограничение доступа

Используется whitelist, если whitelist в config.yaml - пустой, то доступ открыт для всех. В список добавляйте telegram uid разрешённых пользователей.

```
whitelist:
  - uid1
  - uid2
```


## Использование LoRA

В config.yaml необходимо добавить свои строки в раздел `loras`. Далее LoRA подключается добавлением в промпт `#имя_LoRA`. Например `#vlozhkin`. Можно указать strength - `#lora_name:0.5`

Формат строки LoRA: `имя для бота`|`имя файла модели LoRA`|`strength по-умолчанию`|`строка, которая будет добавлена в начало промпта`

Пример:

```
loras:
  - 'vlozhkin|vlozhkin3.safetensors|1|vlozhkin style illustration'
```
