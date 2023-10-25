#!/usr/bin/env python

import telebot
import re
import io
import os
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

with open('config.yaml') as f:
    config = yaml.safe_load(f)
    print(config)
    BOT_TOKEN = config['network']['BOT_TOKEN']
    SERVER_ADDRESS = config['network']['SERVER_ADDRESS']

    TRANSLATE = config['bot']['TRANSLATE']
    HELP_TEXT = config['bot']['HELP_TEXT']
    DENY_TEXT = config['bot']['DENY_TEXT']

    DEFAULT_MODEL = config['comfyui']['DEFAULT_MODEL']
    DEFAULT_VAE = config['comfyui']['DEFAULT_VAE']
    DEFAULT_CONTROLNET = config['comfyui']['DEFAULT_CONTROLNET']
    NEGATIVE_PROMPT = config['comfyui']['NEGATIVE_PROMPT']
    BEAUTIFY_PROMPT = config['comfyui']['BEAUTIFY_PROMPT']
    DEFAULT_WIDTH = config['comfyui']['DEFAULT_WIDTH']
    DEFAULT_HEIGHT = config['comfyui']['DEFAULT_HEIGHT']
    MAX_WIDTH = config['comfyui']['MAX_WIDTH']
    MAX_HEIGHT = config['comfyui']['MAX_HEIGHT']
    SAMPLER = config['comfyui']['SAMPLER']
    SAMPLER_STEPS = config['comfyui']['SAMPLER_STEPS']


if not os.path.exists('tmp'):
    os.makedirs('tmp')

if not os.path.exists('img2img'):
    os.makedirs('img2img')


client_id = str(uuid.uuid4())

bot = telebot.TeleBot(BOT_TOKEN)

with open('workflows/i2i.json') as json_file:
    wf_i2i = json.load(json_file)

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


def check_access(id):
    if (config['whitelist'] is None): # Allow all, whitelist is empty
        return True

    if (id in config['whitelist']):
        return True

    bot.send_message(chat_id=id, text=DENY_TEXT)
    return False


def setup_workflow(wf, prompt, source_image = ''):
    workflow = wf
    seed = random.randint(1, 18446744073709519872)

    if TRANSLATE:
        prompt = GoogleTranslator(source='auto', target='en').translate(text=prompt)
    prompt = prompt + BEAUTIFY_PROMPT

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

        if ("steps" in workflow[node]['inputs']):
            workflow[node]['inputs']['steps'] = SAMPLER_STEPS

        if ("text" in workflow[node]['inputs']):
            if (workflow[node]['inputs']['text'] == 'positive prompt'):
               workflow[node]['inputs']['text'] = prompt

        if ("text" in workflow[node]['inputs']):
            if (workflow[node]['inputs']['text'] == 'negative prompt'):
               workflow[node]['inputs']['text'] = NEGATIVE_PROMPT

        if ("image" in workflow[node]['inputs']):
            if (workflow[node]['inputs']['image'] == 'source image'):
               workflow[node]['inputs']['image'] = source_image

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


def t2i(chat, prompts, target_workflow):
    if not check_access(chat.id):
        return

    workflow = setup_workflow(target_workflow, prompts)

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(SERVER_ADDRESS, client_id))
    images = get_images(ws, workflow)

    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            bot.send_photo(chat_id=chat.id, photo=image, caption=prompts)
            tmpn = "tmp/img_" + str(random.randint(0, 55555555555555)) + ".png"
            png = Image.open(io.BytesIO(image_data))
            png.save(tmpn)
            pd = open(tmpn, 'rb')
            bot.send_document(chat_id=chat.id, document=pd)


def i2i(chat, prompts, target_workflow, photo):
    if not check_access(chat.id):
        return

    imf = bot.get_file(photo[len(photo)-1].file_id)
    imgf = bot.download_file(imf.file_path)
    fn = "source_" + str(random.randint(0, 6666666666666)) + ".png"
    with open("img2img/" + fn, 'wb') as new_file:
        new_file.write(imgf)    

    workflow = setup_workflow(target_workflow, prompts, os.getcwd() + "/img2img/" + fn)

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(SERVER_ADDRESS, client_id))
    images = get_images(ws, workflow)

    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            bot.send_photo(chat_id=chat.id, photo=image, caption=prompts)
            tmpn = "tmp/img_" + str(random.randint(0, 55555555555555)) + ".png"
            png = Image.open(io.BytesIO(image_data))
            png.save(tmpn)
            pd = open(tmpn, 'rb')
            bot.send_document(chat_id=chat.id, document=pd)


@bot.message_handler(commands=['help'])
@bot.message_handler(commands=['start'])
def start_message(message):
    print(message.chat)
    bot.send_message(chat_id=message.chat.id, text=HELP_TEXT)


@bot.message_handler(commands=['face'])
def start_message(message):
    print(message.chat)
    t2i(message.chat, message.text.replace("/face", ""), wf_t2i_facefix_upscale)


@bot.message_handler(commands=['upscale'])
def start_message(message):
    print(message.chat)
    t2i(message.chat, message.text.replace("/upscale", ""), wf_t2i_upscale)


@bot.message_handler(content_types='text')
def message_reply(message):
    print('>', message.chat, message.text)
    t2i(message.chat, message.text, wf_t2i)


@bot.message_handler(content_types='photo')
def message_reply(message):
    prompt = message.caption
    wf = wf_i2i
    if ('/face ' in prompt):
        wf = wf_i2i_facefix_upscale
        prompt = prompt.replace('/face ', '')
    if ('/upscale ' in prompt):
        wf = wf_i2i_upscale
        prompt = prompt.replace('/upscale ', '')

    i2i(message.chat, prompt, wf, message.photo)


if __name__ == '__main__':
    bot.infinity_polling()
