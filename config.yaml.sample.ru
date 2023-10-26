network:
  BOT_TOKEN: 'xxx:xxxxxx'
  SERVER_ADDRESS: "127.0.0.1:8188"

bot:
  TRANSLATE: True
  DENY_TEXT: "Access denied"
  HELP_TEXT: "Для генерации можно использовать текст на русском языке

По-умолчанию каритнка создаётся в разрешении 512x512 пикселей

В промпте можно указать размер ШИРИНАxВЫСОТА. Например - 1024x512

Для добавления негативного промпта - добавить его в конец сообщения через разделитель '|'

Команды:

/upscale .... - создаст картинку высокого разрешения

/face .... - исправит дефекты лиц"

comfyui:
  DEFAULT_MODEL: 'revAnimatedFp16_122.safetensors'
  DEFAULT_CONTROLNET: 'control_v11f1e_sd15_tile.pth'
  DEFAULT_VAE: 'vaeFtMse840000Ema_v10.safetensors'
  DEFAULT_UPSCALER: '4xNMKDSuperscale_4xNMKDSuperscale.pt'
  SCHEDULER: 'karras'                 
  SAMPLER: 'uni_pc'
  SAMPLER_STEPS: 30
  TOKEN_MERGE_RATIO: '0.6'
  CLIP_SKIP: '-1'
  CONTROLNET_STRENGTH: '1.0'
  DEFAULT_WIDTH: 512
  DEFAULT_HEIGHT: 512
  MAX_WIDTH: 2048      
  MAX_HEIGHT: 2048
  BEAUTIFY_PROMPT: ',masterpiece, perfect, small details, highly detailed, best, high quality, professional photo'
  NEGATIVE_PROMPT: 'low quality, worst quality, embedding:badhandv4, blurred, deformed, embedding:EasyNegative, embedding:badquality, watermark, text, font, signage, artist name, text, caption, jpeg artifacts'

whitelist:
