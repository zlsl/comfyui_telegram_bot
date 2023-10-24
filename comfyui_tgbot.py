#!/usr/bin/env python

import telebot
import io
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

    DEFAULT_MODEL = config['comfyui']['DEFAULT_MODEL']
    NEGATIVE_PROMPT = config['comfyui']['NEGATIVE_PROMPT']
    DEFAULT_WIDTH = config['comfyui']['DEFAULT_WIDTH']
    DEFAULT_HEIGHT = config['comfyui']['DEFAULT_HEIGHT']
    SAMPLER = config['comfyui']['SAMPLER']
    SAMPLER_STEPS = config['comfyui']['SAMPLER_STEPS']


client_id = str(uuid.uuid4())

bot = telebot.TeleBot(BOT_TOKEN)

with open('workflows/i2i.json') as json_file:
    wf_i2i = json.load(json_file)

with open('workflows/t2i.json') as json_file:
    wf_t2i = json.load(json_file)

with open('workflows/t2i_facefix_upscale.json') as json_file:
    wf_t2i_facefix_upscale = json.load(json_file)

with open('workflows/t2i_upscale.json') as json_file:
    wf_t2i_upscale = json.load(json_file)


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
    orig = prompts

    workflow = target_workflow
    workflow["48"]["inputs"]["seed"] = random.randint(1, 99999999999999) 
    workflow["163"]["inputs"]["ckpt_name"] = DEFAULT_MODEL 

    workflow["164"]["inputs"]["width"] = DEFAULT_WIDTH
    workflow["164"]["inputs"]["height"] = DEFAULT_HEIGHT

    workflow["48"]["inputs"]["sampler_name"] = SAMPLER
    workflow["48"]["inputs"]["steps"] = SAMPLER_STEPS

    if ("512*" in prompts):
        workflow["164"]["inputs"]["width"] = 512
        prompts = prompts.replace("512", "")

    if ("768*" in prompts):
        workflow["164"]["inputs"]["width"] = 768
        prompts = prompts.replace("768", "")

    if ("1024*" in prompts):
        workflow["164"]["inputs"]["width"] = 1024
        prompts = prompts.replace("1024", "")

    if ("*512" in prompts):
        workflow["164"]["inputs"]["height"] = 512
        prompts = prompts.replace("*512", "")
    
    if ("*768" in prompts):
        workflow["164"]["inputs"]["height"] = 768
        prompts = prompts.replace("*768", "")

    if ("*1024" in prompts):
        workflow["164"]["inputs"]["height"] = 1024
        prompts = prompts.replace("*1024", "")

    if TRANSLATE:
        prompts = GoogleTranslator(source='auto', target='en').translate(text=prompts)
    prompts = prompts + ",masterpiece, perfect, small details, highly detailed, best, high quality, professional photo"


    workflow["97"]["inputs"]["text"] = prompts
    workflow["98"]["inputs"]["text"] = NEGATIVE_PROMPT

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(SERVER_ADDRESS, client_id))
    images = get_images(ws, workflow)

    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            bot.send_photo(chat_id=chat.id, photo=image, caption=orig)
            tmpn = "tmp/img_" + str(random.randint(0, 55555555555555)) + ".png"
            png = Image.open(io.BytesIO(image_data))
            png.save(tmpn)
            pd = open(tmpn, 'rb')
            bot.send_document(chat_id=chat.id, document=pd)


def i2i(chat, prompts, target_workflow, photo):
    imf = bot.get_file(photo[len(photo)-1].file_id)
    imgf = bot.download_file(imf.file_path)
    fn = "source_" + str(random.randint(0, 6666666666666)) + ".png"
    with open("img2img/" + fn, 'wb') as new_file:
        new_file.write(imgf)    

    orig = prompts

    workflow = target_workflow
    workflow["1"]["inputs"]["ckpt_name"] = DEFAULT_MODEL 
    workflow["11"]["inputs"]["noise_seed"] = random.randint(1, 99999999999999)
    workflow["6"]["inputs"]["image"] = "/zstorage/fast1/bots/comfybot/img2img/" + fn 

    workflow["11"]["inputs"]["sampler_name"] = SAMPLER
    workflow["11"]["inputs"]["steps"] = SAMPLER_STEPS

    workflow["16"]["inputs"]["width"] = DEFAULT_WIDTH
    workflow["16"]["inputs"]["height"] = DEFAULT_HEIGHT

    if ("512*" in prompts):
        workflow["16"]["inputs"]["width"] = 512
        prompts = prompts.replace("512*", "*")

    if ("768*" in prompts):
        workflow["16"]["inputs"]["width"] = 768
        prompts = prompts.replace("768*", "*")

    if ("1024*" in prompts):
        workflow["16"]["inputs"]["width"] = 1024
        prompts = prompts.replace("1024*", "*")

    if ("*512" in prompts):
        workflow["16"]["inputs"]["height"] = 512
        prompts = prompts.replace("*512", "")
    
    if ("*768" in prompts):
        workflow["16"]["inputs"]["height"] = 768
        prompts = prompts.replace("*768", "")

    if ("*1024" in prompts):
        workflow["16"]["inputs"]["height"] = 1024
        prompts = prompts.replace("*1024", "")

    if TRANSLATE:
        prompts = GoogleTranslator(source='auto', target='en').translate(text=prompts)
    prompts = prompts + ",masterpiece, perfect, small details, highly detailed, best, high quality, professional photo"


    workflow["4"]["inputs"]["text"] = prompts
    workflow["5"]["inputs"]["text"] = NEGATIVE_PROMPT

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(SERVER_ADDRESS, client_id))
    images = get_images(ws, workflow)

    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            bot.send_photo(chat_id=chat.id, photo=image, caption=orig)
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
    i2i(message.chat, message.caption, wf_i2i, message.photo)



if __name__ == '__main__':
    bot.infinity_polling()

