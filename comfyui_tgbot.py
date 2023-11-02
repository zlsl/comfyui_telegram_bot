#!/usr/bin/env python

import logging
import os, sys
import coloredlogs

logging.basicConfig(filename='bot.log', encoding='utf-8')

log = logging.getLogger()
coloredlogs.install(level=logging.INFO, logger=log, fmt='%(levelname)s %(message)s')

if not os.path.exists('config.yaml'):
    log.critical("No config.yaml file found!")
    sys.exit(os.EX_CONFIG) 

import time
import copy
import re
import io
import asyncio
import telebot
from telebot.async_telebot import AsyncTeleBot
import random
from PIL import Image
from deep_translator import GoogleTranslator
from PIL import Image, ImageEnhance
import websocket
import uuid
import json
import yaml
import urllib.request
import urllib.parse
from sanitize_filename import sanitize

with open('config.yaml') as f:
    config = yaml.safe_load(f)
    BOT_TOKEN = config['network']['BOT_TOKEN']
    SERVER_ADDRESS = config['network']['SERVER_ADDRESS']

    TRANSLATE = config['bot']['TRANSLATE']
    HELP_TEXT = config['bot']['HELP_TEXT']
    DENY_TEXT = config['bot']['DENY_TEXT']

    DEFAULT_MODEL = config['comfyui']['DEFAULT_MODEL']
    DEFAULT_VAE = config['comfyui']['DEFAULT_VAE']
    DEFAULT_CONTROLNET = config['comfyui']['DEFAULT_CONTROLNET']
    CONTROLNET_STRENGTH = config['comfyui']['CONTROLNET_STRENGTH']
    DEFAULT_UPSCALER = config['comfyui']['DEFAULT_UPSCALER']
    NEGATIVE_PROMPT = config['comfyui']['NEGATIVE_PROMPT']
    BEAUTIFY_PROMPT = config['comfyui']['BEAUTIFY_PROMPT']
    DEFAULT_WIDTH = config['comfyui']['DEFAULT_WIDTH']
    DEFAULT_HEIGHT = config['comfyui']['DEFAULT_HEIGHT']
    MAX_WIDTH = config['comfyui']['MAX_WIDTH']
    MAX_HEIGHT = config['comfyui']['MAX_HEIGHT']
    SCHEDULER = config['comfyui']['SCHEDULER']
    SAMPLER = config['comfyui']['SAMPLER']
    SAMPLER_STEPS = config['comfyui']['SAMPLER_STEPS']
    TOKEN_MERGE_RATIO = config['comfyui']['TOKEN_MERGE_RATIO']
    CLIP_SKIP = config['comfyui']['CLIP_SKIP']
    ALLOW_DIRECT_LORA = config['comfyui']['ALLOW_DIRECT_LORA']

if not os.path.exists('tmp'):
    log.info("Creating tmp folder")
    os.makedirs('tmp')

if not os.path.exists('img2img'):
    log.info("Creating img2img folder")
    os.makedirs('img2img')

if (config['whitelist'] is None): # Allow all, whitelist is empty
    log.warning("Whitelist is empty, all users allowed to access this bot! Modify config.yaml")


loras = []
if (config['loras'] is not None): # Has loras
    for lora in config['loras']:
        tmp = lora.split('|')
        if (len(tmp) == 4):
            log.info('Add LoRA - ' + tmp[1])
            loras.append({
                'name': tmp[0],
                'lora_file': tmp[1],
                'strength': tmp[2],
                'prompt': tmp[3]
                })


def get_lora(prompt):
    lr = re.findall('\\#\\w+\\:?\\d*.?\\d*', prompt) #\\#\\w+

    if lr:
        lr = lr[0].replace('#', '').strip()
        if (":" in lr): # strength
            tmp = lr.split(':')
            lr = tmp[0]
            strength = tmp[1]
        else:
            strength = None
        for lora in loras:
            if lora['name'] == lr:
                if strength:
                    lora = copy.deepcopy(lora)
                    lora['strength'] = strength
                    log.info("Lora: " + lora['name'])
                return lora
    return False


client_id = str(uuid.uuid4())

bot = AsyncTeleBot(BOT_TOKEN)

with open('workflows/i2i.json') as json_file:
    wf_i2i = json.load(json_file)

with open('workflows/lora_i2i.json') as json_file:
    wf_lora_i2i = json.load(json_file)

with open('workflows/lora_i2i_upscale.json') as json_file:
    wf_lora_i2i_upscale = json.load(json_file)

with open('workflows/lora_i2i_facefix_upscale.json') as json_file:
    wf_lora_i2i_facefix_upscale = json.load(json_file)

with open('workflows/i2i_upscale.json') as json_file:
    wf_i2i_upscale = json.load(json_file)

with open('workflows/i2i_facefix_upscale.json') as json_file:
    wf_i2i_facefix_upscale = json.load(json_file)

with open('workflows/t2i.json') as json_file:
    wf_t2i = json.load(json_file)

with open('workflows/t2i_facefix_upscale.json') as json_file:
    wf_t2i_facefix_upscale = json.load(json_file)

with open('workflows/t2i_upscale.json') as json_file:
    wf_t2i_upscale = json.load(json_file)

with open('workflows/lora_t2i.json') as json_file:
    wf_lora_t2i = json.load(json_file)

with open('workflows/lora_t2i_facefix_upscale.json') as json_file:
    wf_lora_t2i_facefix_upscale = json.load(json_file)

with open('workflows/lora_t2i_upscale.json') as json_file:
    wf_lora_t2i_upscale = json.load(json_file)


async def check_access(id):
    if (config['whitelist'] is None): # Allow all, whitelist is empty
        log.info("Access allowed for %s, empty whitelist in config yaml", id)
        return True

    if (id in config['whitelist']):
        log.info("Access allowed for %s, user in whitelist", id)
        return True

    await bot.send_message(chat_id=id, text=DENY_TEXT)
    log.warning("Access denied for %s, user not in whitelist", id)
    return False


def setup_workflow(wf, prompt, source_image = '', lora = None):
    workflow = copy.deepcopy(wf)
    seed = random.randint(1, 18446744073709519872)

    if TRANSLATE:
        prompt = GoogleTranslator(source='auto', target='en').translate(text=prompt)

    if ('|' in prompt): #got negative prompt part
        ps = prompt.split('|')
        prompt = ps[0].strip() + BEAUTIFY_PROMPT
        negative_prompt = ps[1].strip()
    else:
        prompt = prompt# + BEAUTIFY_PROMPT
        negative_prompt = NEGATIVE_PROMPT

    if lora:
        prompt = lora['prompt'] + ',' + prompt
        prompt = prompt.replace('#' + lora['name'], '')

    sizes = re.findall('\d+x\d+', prompt)
    if sizes:
        dimensions = sizes[0].split('x')
        width = dimensions[0]
        height = dimensions[1]
        prompt = prompt.replace(sizes[0], '')
    else:
        width = DEFAULT_WIDTH
        if (width > MAX_WIDTH):
            width = MAX_WIDTH

        height = DEFAULT_HEIGHT
        if (height > MAX_HEIGHT):
            width = MAX_HEIGHT

    for node in workflow:
        if ("ckpt_name" in workflow[node]['inputs']):
            workflow[node]['inputs']['ckpt_name'] = DEFAULT_MODEL

        if ("vae_name" in workflow[node]['inputs']):
            workflow[node]['inputs']['vae_name'] = DEFAULT_VAE

        if ("control_net_name" in workflow[node]['inputs']):
            workflow[node]['inputs']['control_net_name'] = DEFAULT_CONTROLNET

        if ("strength" in workflow[node]['inputs']):
            if (workflow[node]['class_type'] == 'ControlNetApply'):
               workflow[node]['inputs']['strength'] = CONTROLNET_STRENGTH

        if ("width" in workflow[node]['inputs']):
            workflow[node]['inputs']['width'] = width

        if ("height" in workflow[node]['inputs']):
            workflow[node]['inputs']['height'] = height

        if ("seed" in workflow[node]['inputs']):
            workflow[node]['inputs']['seed'] = seed

        if ("noise_seed" in workflow[node]['inputs']):
            workflow[node]['inputs']['noise_seed'] = seed

        if ("sampler_name" in workflow[node]['inputs']):
            workflow[node]['inputs']['sampler_name'] = SAMPLER

        if ("scheduler" in workflow[node]['inputs']):
            workflow[node]['inputs']['scheduler'] = SCHEDULER

        if ("steps" in workflow[node]['inputs']):
            workflow[node]['inputs']['steps'] = SAMPLER_STEPS

        if ("stop_at_clip_layer" in workflow[node]['inputs']):
            workflow[node]['inputs']['stop_at_clip_layer'] = CLIP_SKIP

        if ("text" in workflow[node]['inputs']):
            if (workflow[node]['inputs']['text'] == 'positive prompt'):
               workflow[node]['inputs']['text'] = prompt

        if ("text" in workflow[node]['inputs']):
            if (workflow[node]['inputs']['text'] == 'negative prompt'):
               workflow[node]['inputs']['text'] = negative_prompt

        if ("image" in workflow[node]['inputs']):
            if (workflow[node]['inputs']['image'] == 'source image'):
               workflow[node]['inputs']['image'] = source_image

        if ("model_name" in workflow[node]['inputs']):
            if (workflow[node]['class_type'] == 'UpscaleModelLoader'):
               workflow[node]['inputs']['model_name'] = DEFAULT_UPSCALER
        
        if ("ratio" in workflow[node]['inputs']):
            if (workflow[node]['class_type'] == 'TomePatchModel'):
               workflow[node]['inputs']['ratio'] = TOKEN_MERGE_RATIO

        if lora:
            if ("lora_name" in workflow[node]['inputs']):
                workflow[node]['inputs']['lora_name'] = lora['lora_file']
                workflow[node]['inputs']['strength_model'] = lora['strength']

#    print(json.dumps(workflow, indent=2))

    return workflow


def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(SERVER_ADDRESS), data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(SERVER_ADDRESS, url_values)) as response:
        return response.read()


def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(SERVER_ADDRESS, prompt_id)) as response:
        return json.loads(response.read())


def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break
        else:
            continue

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images


async def t2i(chat, prompts, target_workflow, lora):
    if not await check_access(chat.id):
        return

    workflow = setup_workflow(target_workflow, prompts)

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(SERVER_ADDRESS, client_id))
    images = get_images(ws, workflow)

    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            try:
                await bot.send_photo(chat_id=chat.id, photo=image, caption=prompts)
            except:
                log.error("Error sending photo")
            tmpn = "tmp/img_" + str(chat.id) + "_" + sanitize(prompts[0:100]) + "_" + str(random.randint(0, 55555555555555)) + ".png"
            png = Image.open(io.BytesIO(image_data))
            png.save(tmpn)
            pd = open(tmpn, 'rb')
            await bot.send_document(chat_id=chat.id, document=pd)


async def i2i(chat, prompts, target_workflow, photo, lora):
    if not await check_access(chat.id):
        return

    img_id = photo[len(photo)-1].file_id
    tmp = (await bot.get_file(img_id))
    imgf = (await bot.download_file(tmp.file_path))

    fn = "source_" + str(chat.id) + "_" + str(random.randint(0, 6666666666666)) + ".png"
    with open("img2img/" + fn, 'wb') as new_file:
        new_file.write(imgf)    

    workflow = setup_workflow(target_workflow, prompts, os.getcwd() + "/img2img/" + fn, lora)

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(SERVER_ADDRESS, client_id))
    images = get_images(ws, workflow)

    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            try:
                await bot.send_photo(chat_id=chat.id, photo=image, caption=prompts)
            except:
                log.error("Error sending photo")
            tmpn = "tmp/img_" + str(chat.id) + "_" + sanitize(prompts[0:100]) + "_" + str(random.randint(0, 55555555555555)) + ".png"
            png = Image.open(io.BytesIO(image_data))
            png.save(tmpn)
            pd = open(tmpn, 'rb')
            await bot.send_document(chat_id=chat.id, document=pd)


@bot.message_handler(commands=['help'])
@bot.message_handler(commands=['start'])
async def start_message(message):
    print(message.chat)
    await bot.send_message(chat_id=message.chat.id, text=HELP_TEXT)


@bot.message_handler(content_types='text')
async def message_reply(message):
    log.info("T2I:%s (%s %s) '%s'", message.chat.id, message.chat.first_name, message.chat.username, message.text)
    prompt = message.text
    wf = wf_t2i
    lora = get_lora(prompt)
    if lora:
        wf = wf_lora_t2i
        if ('/face' in prompt):
            wf = wf_lora_t2i_facefix_upscale
            prompt = prompt.replace('/face', '')
        if ('/upscale' in prompt):
            wf = wf_lora_t2i_upscale
            prompt = prompt.replace('/upscale', '')
    else:
        if ('/face' in prompt):
            wf = wf_t2i_facefix_upscale
            prompt = prompt.replace('/face', '')
        if ('/upscale' in prompt):
            wf = wf_t2i_upscale
            prompt = prompt.replace('/upscale', '')

    await t2i(message.chat, message.text, wf, lora)


@bot.message_handler(content_types='photo')
async def message_reply(message):
    log.info("I2I:%s (%s %s) '%s'", message.chat.id, message.chat.first_name, message.chat.username, message.caption)
    prompt = message.caption
    wf = wf_i2i
    lora = get_lora(prompt)
    if lora:
        wf = wf_lora_i2i
        if ('/face' in prompt):
            wf = wf_lora_i2i_facefix_upscale
            prompt = prompt.replace('/face', '')
        if ('/upscale' in prompt):
            wf = wf_lora_i2i_upscale
            prompt = prompt.replace('/upscale', '')
    else:
        if ('/face' in prompt):
            wf = wf_i2i_facefix_upscale
            prompt = prompt.replace('/face', '')
        if ('/upscale' in prompt):
            wf = wf_i2i_upscale
            prompt = prompt.replace('/upscale', '')

    await i2i(message.chat, prompt, wf, message.photo, lora)


log.info("Starting bot")

if __name__ == '__main__':
    asyncio.run(bot.infinity_polling())
