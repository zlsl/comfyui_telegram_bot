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
  DEFAULT_WIDTH: 512
  DEFAULT_HEIGHT: 512
  MAX_WIDTH: 2048 - ограничение ширины     
  MAX_HEIGHT: 2048 - ограничение высоты
  BEAUTIFY_PROMPT: ',masterpiece, perfect, small details, highly detailed, best, high quality, professional photo' - добавляется к промпту
  NEGATIVE_PROMPT: 'low quality, worst quality, embedding:badhandv4, blurred, deformed, embedding:EasyNegative, embedding:badquality, watermark, text, font, signage, artist name, text, caption, jpeg artifacts' - настройте под свои нужды негативный промпт
```

## Описание работы

Используются различные workflow для генерации, в каталоги workflows они находятся в формате ComfyUI API

По-умолчанию при получении чистого промпта генерируется картинка с размерами DEFAULT_WIDTHxDEFAULT_HEIGHT, размер можно указывать в формате WIDTHxHEIGHT

Ответом от бота будут два сообщения: картинка (с потерей качетсва из-за сжатия телеграмом) и PNG файл с исходным качеством.

Если боту отправить картинку, то картинка будет преобразована, согласно промпту, в данном случае команды `/face`, `/upscale` также работают. Важно! Для img2img использутеся COntrolNet, а не классический денойс,что позволяет дать максимально приближенный к оригиналу результат.

Для добавления своего негативного промпта вместо встроенного - можно добавить к сообщению через разделитель `|`

Исходная картинка | Результат
--- | ---
![Исходная картинка](https://raw.githubusercontent.com/zlsl/comfyui_telegram_bot/main/examples/i2i_src.jpg) | ![Исходная картинка](https://raw.githubusercontent.com/zlsl/comfyui_telegram_bot/main/examples/i2i_result.jpg) Милый демон с белой змеиной чешуёй, изумрудные глаза, острые когти 1024x1024


В каталоге img2img сохраняются картинки отправленные боту

Каталог tmp - результаты генераций


## Команды

`/start`, `/help` - информация об использовании из HELP_TEXT

`/upscale` - апскейл готовой картинки

`/face` - с коррекцией лиц и апскейлом (каждое лицо на картинке увеличит время генерации)


## Ограничение доступа

Используется whitelist, если whitelist в config.yaml - пустой, то доступ открыт для всех. В список добавляйте telegram uid разрешённых пользователей.

```
whitelist:
  - uid1
  - uid2
```


## Использование LoRA

В config.yaml необходимо добавить свои строки в раздел `loras`. Далее LoRA подключается добавлением в промпт `#имя_LoRA`. Например `#vlozhkin`

Формат строки LoRA: `имя для бота`|`имя файла модели LoRA`|`strength по-умолчанию`|`строка, которая будет добавлена в начало промпта`

Пример:

```
loras:
  - 'vlozhkin|vlozhkin3.safetensors|1|vlozhkin style illustration'
```


## Как добавить свой workflow

Используются следующий файлы:

- t2i.json - базовый text2image
- t2i_upscale.json - text2image с апскейлом
- t2i_facefix_upscale.json - text2image с апскейлом и фиксом лиц
- i2i.json - базовый image2image
- i2i_upscale.json - image2image с апскейлом
- i2i_facefix_upscale.json - image2image с апскейлом и фиксом лиц

В ComfyUI необходимо включить dev режим (в настройках), появится пункт меню *Save (API Format)*

В workflow необходимо:

1. В тексте с ClipTextEncode для позитивного промпта поставить значение `positive prompt`
2. В тексте с ClipTextEncode для негативного промпта поставить значение `negative prompt`
3. Для image2image в коде json файла выставить в блоке `LoadImage` значение "inputs" - "image" в *source image*

Пример фрагмента json:

```
"4": {
    "inputs": {
      "text": "positive prompt",
      "clip": [
        "1",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "5": {
    "inputs": {
      "text": "negative prompt",
      "clip": [
        "1",
        1
      ]
    },
    "class_type": "CLIPTextEncode"
  },
  "6": {
    "inputs": {
      "image": "source image",
      "choose file to upload": "image"
    },
    "class_type": "LoadImage"
  },
```
