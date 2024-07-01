import google.generativeai as genai
from IPython.display import display, Markdown
from PIL import Image
from PIL import ExifTags
from iptcinfo3 import IPTCInfo
import pathlib
import textwrap
import csv
import os
import configparser
import time
import piexif

def read_config():
  config = configparser.ConfigParser()
  config.read('config/metain.conf')
  config_values = {
    'gemini_api_key': config.get('API', 'gemini_api_key'),
    'gemini_model': config.get('API', 'gemini_model'),
    'input_dir': config.get('File', 'input_dir')
  }
  return config_values

# Configure the API key
genai.configure(api_key=read_config()['gemini_api_key'])
# Initialize the generative model
model = genai.GenerativeModel(read_config()['gemini_model'])

# Define the categories (Adobe Stock Categories)
categories = {
    1: 'Animals',
    2: 'Buildings and Architecture',
    3: 'Business',
    4: 'Drinks',
    5: 'The Environment',
    6: 'States of Mind',
    7: 'Food',
    8: 'Graphic Resources',
    9: 'Hobbies and Leisure',
    10: 'Industry',
    11: 'Landscapes',
    12: 'Lifestyle',
    13: 'People',
    14: 'Plants and Flowers',
    15: 'Culture and Religion',
    16: 'Science',
    17: 'Social Issues',
    18: 'Sports',
    19: 'Technology',
    20: 'Transport',
    21: 'Travel'
}

# prompt = (
#     "generate prompt or description (minimum 50 letters, max 99 letters). keywords (max 49 keywords) for submitting this image to a stock photo site. "
#     "Also provide a category for the image from the following list: "
#     "Animals, Buildings and Architecture, Business, Drinks, The Environment, States of Mind, Food, "
#     "Graphic Resources, Hobbies and Leisure, Industry, Landscapes, Lifestyle, People, Plants and Flowers, "
#     "Culture and Religion, Science, Social Issues, Sports, Technology, Transport, Travel. "
#     "The response should be in the format: 'Prompt: <prompt>. Keywords: <keywords>. Category: <category>'."
# )

# Reverse categories dictionary to map category names to numbers
category_map = {v: k for k, v in categories.items()}

image_files = list(pathlib.Path(read_config()['input_dir']).glob('*.png')) + \
              list(pathlib.Path(read_config()['input_dir']).glob('*.jpg')) + \
              list(pathlib.Path(read_config()['input_dir']).glob('*.jpeg')) + \
              list(pathlib.Path(read_config()['input_dir']).glob('*.PNG')) + \
              list(pathlib.Path(read_config()['input_dir']).glob('*.JPG')) + \
              list(pathlib.Path(read_config()['input_dir']).glob('*.JPEG'))

# Function to clean text
def clean_text(text):
    return text.replace('#', '').replace('title', '').replace('Title', '').replace(':', '').replace('*', '').strip()

def decode_keywords(elist, charset):
    dlist = []
    for l in elist:
        dlist.append(l.decode(charset))
    return dlist

def encode_keywords(dlist, charset):
    elist = []
    for l in dlist:
        elist.append(l.strip().encode(charset))
    return elist

error_files = []
# prompt = (
#     "Generate metadata consisting Title, Description, Keywords and Category for the submitted image to the microstock agency. "
#     "The metadata must be relevant to submit to microstock agency such ase Shutterstock, Adobe Stock, Freepik, etc. "
#     "Title has a minimum of 50 letters and a maximum of 99 letters. "
#     "Description has a minimum 50 letters and a maximum of 100 letters. "
#     # "Keywords has a minimum of 30 keywords and a maximum of 50 keywords, also include the phrases in the title as keywords. Prioritize that each keyword only contains 1 syllable or a maximum of 2 syllables."
#     "Keywords has a minimum of 30 keywords and a maximum of 50 keywords. Include the phrases in the title as keywords. Each keyword only contains 1 word, but sometimes 2 words would be fine. Avoid to repeat same keyword."
#     "Provide a category for the image from the following list: "
#     "[Animals, Buildings and Architecture, Business, Drinks, The Environment, States of Mind, Food, "
#     "Graphic Resources, Hobbies and Leisure, Industry, Landscapes, Lifestyle, People, Plants and Flowers, "
#     "Culture and Religion, Science, Social Issues, Sports, Technology, Transport, Travel] "

#     "The response should be in the format: 'Title: <title>. Description: <description>. Keywords: <keywords>. Category: <category>'. "
# )
prompt_file = open("config/prompt.conf", "r")
prompt = prompt_file.read()

for ifile in image_files:
    img = Image.open(ifile)
    img_small = img
    img_small = img_small.resize((int(img_small.size[0]/4),int(img_small.size[1]/4)))

    print(f"Nama: {ifile}")

    try:
        response = model.generate_content([prompt, img_small], stream=False)
        response_text = response.text
        print(f"Response: {response_text}")

        if "Keywords:" in response_text and "Category:" in response_text:
            title, rest = response_text.split("Description:", 1)
            description, rest = rest.split("Keywords:", 1)
            keywords, category = rest.split("Category:", 1)
            title = clean_text(title.replace("Title:", "").strip())
            description = clean_text(description.strip())
            keywords = clean_text(keywords.strip())
            category = clean_text(category.replace('.', '').strip())
        else:
            raise ValueError("Response format is incorrect.")

        category_number = category_map.get(category, "")

        print(f"Filename: {ifile.name}")
        print(f"Title: {title}")
        print(f"Description: {description}")
        print(f"Keywords: {keywords}")
        print(f"Category: {category}")
        print("--------------------------------------")

        # Delete the image file after writing data to CSV
        # os.remove(image_file)

        list_keywords = [k.lower().replace('.', '').strip() for k in keywords.split(',')]
        uniq_keywords = list(set(list_keywords))

        # img_exif = img.getexif()
        # # Set the EXIF Values Defined at the Top of This Script
        # img_exif[40091] = title.encode('utf16') # Title
        # img_exif[40095] = title.encode('utf16') # Description
        # img_exif[0x9C9E] = '; '.join(uniq_keywords).encode('utf16') # Keywords
        # # Save the Image with the Updated EXIF Data
        # img.save(str(ifile), "JPEG", exif=img_exif, optimize=False, quality=100)
        # Close the Image
        img_small.close()
        img.close()

        info = IPTCInfo(str(ifile), force=True)
        info['headline'] = title.encode('ASCII')
        info['object name'] = title.encode('ASCII')
        info['caption/abstract'] = title.encode('ASCII')
        info['keywords'] = encode_keywords(uniq_keywords, 'ASCII')
        info.save()

        try:
            os.remove(f"{str(ifile)}~")
        except OSError:
            pass
    except Exception as e:
        error_files.append(ifile.name)
        print(f"Error processing {ifile.name}: {e}")

    time.sleep(2)

prompt_file.close()
# print(f"Metadata for {len(image_files) - len(error_files)} images has been written to {output_csv_path}.")
print("Error encountered for these files:")
for error_file in error_files:
    print(error_file)
