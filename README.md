# ComfyUI telegram bot

## Установка и настройка

Необходима рабочая установка ComfyUI с дополнительными модулями:

- ComfyUI-Impact-Pack
- ComfyUI_UltimateSDUpscale

Необходима также установка моделей для сегментации: *face_yolov8m.pt*

Апскейлер: *4xNMKDSuperscale_4xNMKDSuperscale.pt*

ControlNet модель: *control_v11f1e_sd15_tile.pth*

Переименовать файл config.yaml.samlpe в config.yaml и настроить под себя:
```
network:
  BOT_TOKEN: 'xxx:xxxxxx' - токен telegram бота
  SERVER_ADDRESS: "127.0.0.1:8188" - адрес API ComfyUI

bot:
  TRANSLATE: True - Переводить ли языки промпта на английский (через deep_translate)
  HELP_TEXT: "Для генерации можно использовать текст на русском языке
По-умолчанию каритнка создаётся в разрешении 512x512 пикселей
В промпте можно указать размер ШИРИНА*ВЫСОТА, допустимые значения: 512, 768, 1024. Например - 1024*512
Команды:
/upscale .... - создаст картинку высокого разрешения
/face .... - исправит дефекты лиц"

comfyui:
  DEFAULT_MODEL: 'revAnimatedFp16_122.safetensors' - имя модели по-умолчанию
  DEFAULT_VAE: 'vaeFtMse840000Ema_v10.safetensors' - имя VAE модели по-умолчанию
  SAMPLER: 'uni_pc' - используемый сэмплер
  SAMPLER_STEPS: 30 - количество шагов денойса
  DEFAULT_WIDTH: 512
  DEFAULT_HEIGHT: 512
  NEGATIVE_PROMPT: 'low quality, worst quality, embedding:badhandv4, blurred, deformed, embedding:EasyNegative, embedding:badquality, watermark, text, font, signage, artist name, text, caption, jpeg artifacts' - настройте под свои нужды негативный промпт
```

## Описание работы

Используются различные workflow для генерации, в каталоги workflows они находятся в формате ComfyUI API

По-умолчанию при получении чистого промпта генерируется картинка с размерами DEFAULT_WIDTH x DEFAULT_HEIGHT, размер можно указывать в формате WIDTH*HEIGHT, допустимые размерности - 512, 768, 1024

Ответом от бота будут два сообщения: картинка (с потерей качетсва из-за сжатия телеграмом) и PNG файл с исходным качеством.

Если боту отправить картинку, то картинка будет преобразована, согласно промпту, в данном случае команды `/face`, `/upscale` также работают. Важно! Для img2img использутеся COntrolNet, а не классический денойс,что позволяет дать максимально приближенный к оригиналу результат.

Исходная картинка | Результат
--- | ---
![Исходная картинка](https://raw.githubusercontent.com/zlsl/comfyui_telegram_bot/main/examples/i2i_src.jpg) | ![Исходная картинка](https://raw.githubusercontent.com/zlsl/comfyui_telegram_bot/main/examples/i2i_result.jpg) Милый демон с белой змеиной чешуёй, изумрудные глаза, острые когти 1024\*1024


В каталоге img2img сохраняются картинки отправленные боту

Каталог tmp - результаты генераций


## Команды

`/start`, `/help` - информация об использовании из HELP_TEXT

`/upscale` - апскейл готовой картинки

`/face` - с коррекцией лиц и апскейлом (каждое лицо на картинке увеличит время генерации)


