import sys
import os
import time
import pandas as pd
import geopandas as gpd

from pydantic import BaseModel
from openai import OpenAI

import configparser
import json



DataEye_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_eye_constants')
if DataEye_path not in sys.path:
    sys.path.append(DataEye_path)
import data_eye_constants as eye_constants


# current_script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(parent_dir, 'config.ini')

config = configparser.ConfigParser()
config.read(config_path)
OpenAI_key = config.get('API_Key', 'OpenAI_key')

# SpatialAnalysisAgent_dir = os.path.abspath(os.path.join('..', 'SpatialAnalysisAgent'))
# if SpatialAnalysisAgent_dir not in sys.path:
#     sys.path.append(SpatialAnalysisAgent_dir)





client = OpenAI(api_key=OpenAI_key)


def get_data_overview(data_location_dict):
    data_locations = data_location_dict['data_locations']
    for data in data_locations:
        try:
            meta_str = ''
            format = data['format']
            data_path = data['location']

            # print("data_path:", data_path)

            if (format == 'ESRI shapefile') or (format == 'GeoPackage'):
                meta_str = see_vector(data_path)

            if (format == 'CSV'):
                meta_str = see_table(data_path)

            data['meta_str'] = meta_str
        except Exception as e:
            pass
    return data_location_dict


def add_data_overview_to_data_location(task, data_location_list, model = r'gpt-4o-2024-08-06'):
    prompt = get_prompt_to_pick_up_data_locations(task=task,
                                                  data_locations=data_location_list)
    response = get_LLM_reply(prompt=prompt,
                                    model=model)


    # pprint.pp(result.choices[0].message)
    attributes_json = json.loads(response.choices[0].message.content)

    get_data_overview(attributes_json)



    for idx, data in enumerate(attributes_json['data_locations']):
        meta_str = data['meta_str']
        data_location_list[idx] += ". Data overview: " + meta_str
        # data_location_list[idx] += data_location_list[idx] + " Data overview: " + meta_str
    return attributes_json, data_location_list


def get_prompt_to_pick_up_data_locations(task, data_locations):
    data_locations_str = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(data_locations)])
    prompt = f'Your mission: {eye_constants.mission_prefix} \n\n' + \
             f'Given task description: {task} \n' + \
             f'Data location: \n{data_locations_str}'
    return prompt
def see_table(file_path):
    # print("OK")
    # print(file_path)
    # print(file_path[-3:])
    df = None
    if file_path[-4:].lower() == '.csv':
        # print(file_path)
        df = pd.read_csv(file_path)
    # get_df_types_str
    types_str = _get_df_types_str(df)
    meta_str = types_str

    return meta_str

def _get_df_types_str(df):
    types_str = ', '.join([f"{col}: {dtype}" for col, dtype in df.dtypes.items()])
    types_str = f"[{types_str}]"
    return types_str

def see_vector(file_path):
    gdf = gpd.read_file(file_path)
    types_str = _get_df_types_str(gdf.drop(columns='geometry'))
    # print(gdf.crs)
    crs_summary = str(gdf.crs)  # will be "EPSG:4326", but the original information would be long
    crs_summary = crs_summary.replace('\n', '\t')
    meta_str = str({"column names and data types": types_str, "Coordinate reference system": crs_summary})

    return meta_str

def see_raster(file_path):

    return


# beta vervsion of using structured output. # https://cookbook.openai.com/examples/structured_outputs_intro
# https://platform.openai.com/docs/guides/structured-outputs/examples
def get_LLM_reply(prompt,
                  model=r"gpt-4o",
                  verbose=True,
                  temperature=1,
                  stream=True,
                  retry_cnt=3,
                  sleep_sec=10,
                  ):
    # Generate prompt for ChatGPT
    # url = "https://github.com/gladcolor/LLM-Geo/raw/master/overlay_analysis/NC_tract_population.csv"
    # prompt = prompt + url

    # Query ChatGPT with the prompt
    # if verbose:
    #     print("Geting LLM reply... \n")
    count = 0
    isSucceed = False
    while (not isSucceed) and (count < retry_cnt):
        try:
            count += 1
            response = client.beta.chat.completions.parse(model=model,
                                                      messages=[
                                                          {"role": "system", "content": eye_constants.role},
                                                          {"role": "user", "content": prompt},
                                                      ],
                                                      temperature=temperature,
                                                      response_format=eye_constants.Data_locations,
                                                       )
        except Exception as e:
            # logging.error(f"Error in get_LLM_reply(), will sleep {sleep_sec} seconds, then retry {count}/{retry_cnt}: \n", e)
            print(f"Error in get_LLM_reply(), will sleep {sleep_sec} seconds, then retry {count}/{retry_cnt}: \n",
                  e)
            time.sleep(sleep_sec)

    return response
