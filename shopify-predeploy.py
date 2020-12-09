#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script handles the Continuous Deployment for Shopify projects.
If a new branch is published it creates a new theme for that branch
on the targeted shop. If a branch is updated, the SASS files in it will
be compiled and the whole theme is redeployed to the targeted theme.
This is also true for merging a branch into the development or main branch.

The workflow follows the concept of git-flow (https://nvie.com/posts/a-successful-git-branching-model/)
"""

import glob
import json
import os
import re
import sys

import requests
import yaml

# Global parameter to set Shopify API Version for all relevant API calls
shopifyApiVersion = '2020-10'

def main():
    """Contains the main code for the automatic deployment"""

    print(" ____            _ _         ____        _            \n|  _ \\          | (_)       |  _ \\      | |           \n| |_) | ___ _ __| |_ _ __   | |_) |_   _| |_ ___  ___ \n|  _ < / _ \\ '__| | | '_ \\  |  _ <| | | | __/ _ \\/ __|\n| |_) |  __/ |  | | | | | | | |_) | |_| | ||  __/\\__ \\\n|____/ \\___|_|  |_|_|_| |_| |____/ \\__, |\\__\\___||___/\n                                    __/ |             \n                                   |___/              \n  _____ _                 _  __          _____            _   _                         _____             _                                  _   \n / ____| |               (_)/ _|        / ____|          | | (_)                       |  __ \\           | |                                | |  \n| (___ | |__   ___  _ __  _| |_ _   _  | |     ___  _ __ | |_ _ _ __   ___  _   _ ___  | |  | | ___ _ __ | | ___  _   _ _ __ ___   ___ _ __ | |_ \n \\___ \\| '_ \\ / _ \\| '_ \\| |  _| | | | | |    / _ \\| '_ \\| __| | '_ \\ / _ \\| | | / __| | |  | |/ _ \\ '_ \\| |/ _ \\| | | | '_ ` _ \\ / _ \\ '_ \\| __|\n ____) | | | | (_) | |_) | | | | |_| | | |___| (_) | | | | |_| | | | | (_) | |_| \\__ \\ | |__| |  __/ |_) | | (_) | |_| | | | | | |  __/ | | | |_ \n|_____/|_| |_|\\___/| .__/|_|_|  \\__, |  \\_____\\___/|_| |_|\\__|_|_| |_|\\___/ \\__,_|___/ |_____/ \\___| .__/|_|\\___/ \\__, |_| |_| |_|\\___|_| |_|\\__|\n                   | |           __/ |                                                             | |             __/ |                         \n                   |_|          |___/                                                              |_|            |___/                          \n")

    # Retrieve all parameters
    shopifyDomain = sys.argv[1]
    shopifyUsername = sys.argv[2]
    shopifyPassword = sys.argv[3]
    targetBranch = sys.argv[4]

    # Get a list of all themes
    themes = getAllThemes(shopifyDomain, shopifyUsername, shopifyPassword)
    # Find production and target theme
    themeProduction = findProductionTheme(themes)
    themeTarget = findThemeByName(themes, themeProduction, targetBranch)

    if themeTarget == themeProduction:
        print("Warning! Production theme is targeted!")

    # Create config.yml for theme kit, which includes credentials for production and target theme
    createThemeKitConfig(shopifyDomain, shopifyPassword,
                         themeProduction, themeTarget, targetBranch)

    # Get the settings schema for all sections from the code
    sectionSchemas = getSchemasFromLiquidFromDirectory(
        os.getcwd() + "/src/sections")
    with open('src/config/settings_schema.json', 'r') as settingsSchemaFile:
        settingsSchema = json.load(settingsSchemaFile)
    settingsData = {}
    settingsData["production"] = getSettingsDataFromTheme(
        themeProduction, shopifyDomain, shopifyUsername, shopifyPassword)
    settingsData["target"] = getSettingsDataFromTheme(
        themeTarget, shopifyDomain, shopifyUsername, shopifyPassword)

    if settingsData["target"] is None:
        settingsData["target"] = settingsData["production"]
        print("New theme - Settings were taken from production!")

    settingsData["production"]["current"] = cleanAllSettings(
        settingsData["production"]["current"], settingsSchema, sectionSchemas)
    settingsData["target"]["current"] = cleanAllSettings(
        settingsData["target"]["current"], settingsSchema, sectionSchemas)

    if 'feature/lt-' in targetBranch:
        settingsData["target"] = updateSettingsRecursively(
            settingsData["target"], settingsData["production"])

    updateThemeSettings(themeTarget, settingsData["target"], shopifyDomain,
                        shopifyUsername, shopifyPassword, 'src/config/settings_data.json')

    print("\n\n  ________                __           ____                         _                 \n /_  __/ /_  ____ _____  / /_______   / __/___  _____   __  _______(_)___  ____ _   _ \n  / / / __ \\/ __ `/ __ \\/ //_/ ___/  / /_/ __ \\/ ___/  / / / / ___/ / __ \\/ __ `/  (_)\n / / / / / / /_/ / / / / ,< (__  )  / __/ /_/ / /     / /_/ (__  ) / / / / /_/ /  _   \n/_/ /_/ /_/\\__,_/_/ /_/_/|_/____/  /_/  \\____/_/      \\__,_/____/_/_/ /_/\\__, /  (_)  \n                                                                        /____/        \n\n\n   _____ __                _ ____         ______            __  _                           ____             __                                 __ \n  / ___// /_  ____  ____  (_) __/_  __   / ____/___  ____  / /_(_)___  ____  __  _______   / __ \\___  ____  / /___  __  ______ ___  ___  ____  / /_\n  \\__ \\/ __ \\/ __ \\/ __ \\/ / /_/ / / /  / /   / __ \\/ __ \\/ __/ / __ \\/ __ \\/ / / / ___/  / / / / _ \\/ __ \\/ / __ \\/ / / / __ `__ \\/ _ \\/ __ \\/ __/\n ___/ / / / / /_/ / /_/ / / __/ /_/ /  / /___/ /_/ / / / / /_/ / / / / /_/ / /_/ (__  )  / /_/ /  __/ /_/ / / /_/ / /_/ / / / / / /  __/ / / / /_  \n/____/_/ /_/\\____/ .___/_/_/  \\__, /   \\____/\\____/_/ /_/\\__/_/_/ /_/\\____/\\__,_/____/  /_____/\\___/ .___/_/\\____/\\__, /_/ /_/ /_/\\___/_/ /_/\\__/  \n                /_/          /____/                                                               /_/            /____/                            \n\n\n    __             __                       _____      __         ______                  ______     ____            ___          ____        __           \n   / /_  __  __   / /   ____ ___________   / ___/_____/ /_  ___  / / / /_  ____ ______   / ____ \\   / __ )___  _____/ (_)___     / __ )__  __/ /____  _____\n  / __ \\/ / / /  / /   / __ `/ ___/ ___/   \\__ \\/ ___/ __ \\/ _ \\/ / / __ \\/ __ `/ ___/  / / __ `/  / __  / _ \\/ ___/ / / __ \\   / __  / / / / __/ _ \\/ ___/\n / /_/ / /_/ /  / /___/ /_/ / /  (__  )   ___/ / /__/ / / /  __/ / / / / / /_/ (__  )  / / /_/ /  / /_/ /  __/ /  / / / / / /  / /_/ / /_/ / /_/  __(__  ) \n/_.___/\\__, /  /_____/\\__,_/_/  /____/   /____/\\___/_/ /_/\\___/_/_/_/ /_/\\__,_/____/   \\ \\__,_/  /_____/\\___/_/  /_/_/_/ /_/  /_____/\\__, /\\__/\\___/____/  \n      /____/                                                                            \\____/                                      /____/                 \n")


class BlockUnvalid(Exception):
    """This exception is raised, when a block in the settings isn't defined by a schema."""
    pass


def getAllThemes(shopifyDomain, shopifyUsername, shopifyPassword):
    """Requests a list of all themes from Shopify"""

    r = requests.get(f'https://{shopifyDomain}/admin/api/{shopifyApiVersion}/themes.json',
                     auth=(shopifyUsername, shopifyPassword))
    if r.status_code != 200:
        raise ConnectionError(r.status_code, r.headers)
    return r.json()["themes"]


def findProductionTheme(themes):
    """Gets the currently active theme from Shopify"""

    for theme in themes:
        if theme["role"] == "main":
            return theme


def findThemeByName(themes, themeProduction, targetBranch):
    """Returns the first theme which contains the provided name string."""

    for theme in themes:
        if getThemeNameByBranch(themeProduction, targetBranch) in theme["name"]:
            return theme
    return None


def createThemeKitConfig(shopifyDomain, shopifyPassword, themeProduction, themeTarget, targetBranch):
    """Creates the config.yml file, which is used by Theme Kit to store theme credential."""

    config = {}
    config["productionRO"] = {
        "password": shopifyPassword,
        "theme_id": themeProduction["id"],
        "store":    shopifyDomain,
        "readonly": True
    }

    if (themeTarget is None):
        print("The target theme does not exist. Therefore, it is created.")
        with open('src/new-theme.name', 'w') as newTheme:
            newTheme.write(getThemeNameByBranch(themeProduction, targetBranch))
    else:
        config[targetBranch] = {
            "password": shopifyPassword,
            "theme_id": themeTarget["id"],
            "store":    shopifyDomain,
            "ignore_files": [
                "config.yml",
                "new-theme.name",
                "preview-link.txt"
            ]
        }
        with open('preview-link.txt', 'w') as newTheme:
            newTheme.write('https://' + shopifyDomain + '/?preview_theme_id=' + str(themeTarget["id"]))

    with open("src/config.yml", "w") as configFile:
        yaml.dump(config, configFile, default_flow_style=False)


def getThemeNameByBranch(themeProduction, targetBranch):
    """Creates a theme name following the name of the production theme, but respecting a maximum length of 50 characters."""

    name = re.sub(r'\((.*?)\)', '(' + targetBranch + ')',
                  themeProduction["name"])
    if len(name) > 50:
        name = name[:49] + ")"
    return name


def getSchemaFromLiquid(filepath):
    """Extracts the JSON schema from a liquid file"""

    content = None

    # Setup regular expressions for finding the start and end of the schema
    regExpSchema = re.compile(r'\{% *schema *%\}')
    regExpSchemaEnd = re.compile(r'\{% *endschema *%\}')

    # Loop through provided file line by line
    with open(filepath, "rt") as liquidFile:
        for line in liquidFile:
            # if the opening tag hasn't been found yet, search for it
            if content is None:
                # if it is found in the current line remove it from the line and append the line to content
                if regExpSchema.search(line):
                    content = []
                    content.append(re.sub(regExpSchema, "", line))
            # else check if the closing tag is in the current line remove it from the line and append the line
            elif regExpSchemaEnd.search(line):
                content.append(re.sub(regExpSchemaEnd, "", line))
                break  # loop when closing tag has been found
            else:
                content.append(line)
    if content:
        content = "".join(content)
        content = json.loads(content)
    return content


def getSchemasFromLiquidFromDirectory(directory):
    """Returns a dictionary with the schemas from all Liquid files in a directory."""

    schemas = {}
    # Get a list of all liquid files in the directory
    files = glob.glob(directory + "/*.liquid")
    # Get the schema for each and add it to schemas
    for file in files:
        filename = os.path.basename(file)
        schemas[os.path.splitext(filename)[0]] = getSchemaFromLiquid(file)

    return schemas


def updateThemeSettings(themeTarget, settingsData, shopifyDomain, shopifyUsername, shopifyPassword, filepath=None):
    """Update theme on the server for the target theme."""

    if filepath is not None:
            with open(filepath, 'w') as settingsFile:
                json.dump(settingsData, settingsFile)

    if themeTarget is None:
        print("New theme - no settings were updated!")
        return False
    else:
        content = {
            "asset": {
                "key": "config/settings_data.json",
                "value": json.dumps(settingsData)
            }
        }
        r = requests.put(f'https://{shopifyDomain}/admin/api/{shopifyApiVersion}/themes/{str(themeTarget["id"])}/assets.json', json=content, auth=(shopifyUsername, shopifyPassword))
        with open("connection.log", 'w') as logfile:
            logfile.write(str(r.status_code))
            logfile.write(str(r.headers))
            logfile.write(str(r.text))
        if r.status_code != 200:
            raise ConnectionError(r.status_code, r.headers)
        else:
            print('Successfully updated settings on Theme: {0}'.format(
                themeTarget["name"]))
        return True


def getSettingsDataFromTheme(theme, shopifyDomain, shopifyUsername, shopifyPassword):
    """Returns a dictionary with all the settings active in the online theme."""

    if theme is None:
        return None
    else:
        r = requests.get(f'https://{shopifyDomain}/admin/api/{shopifyApiVersion}/themes/{str(theme["id"])}/assets.json?asset[key]=config/settings_data.json', auth=(shopifyUsername, shopifyPassword))
        if r.status_code != 200:
            raise ConnectionError(r.status_code, r.headers)
        return json.loads(r.json()["asset"]["value"])


def updateSettingsRecursively(target, source):
    """Update all fields in the target settings, if available in source settings."""

    if isinstance(source, dict):
        for key in source:
            if key in target.keys():
                target[key] = updateSettingsRecursively(
                    target[key], source[key])
            else:
                target[key] = source[key]
    elif isinstance(source, list):
        for item in source:
            if not (item in target) and (len(target) < 25):
                target.append(item)
    else:
        target = source
    return target


def cleanAllSettings(settingsData, settingsSchema, sectionSchemas):
    """Removes all incompatible settings from the settings data."""

    cleanedSettingsData = {}
    sectionsFound = False

    settingIDs = []
    for key in settingsSchema:
        if "settings" in key.keys():
            settingIDs = settingIDs + \
                [setting["id"]
                    for setting in key["settings"] if "id" in setting.keys()]

    for themeSetting in settingsData:
        # Remove all invalid sections, section blocks and section settings
        if themeSetting == "sections":
            cleanedSettingsData["sections"] = cleanAllSectionSettings(
                settingsData["sections"], sectionSchemas, settingsData["content_for_index"])
            sectionsFound = True
        elif themeSetting == "content_for_index":
            cleanedSettingsData["content_for_index"] = settingsData[themeSetting]
        else:
            if (themeSetting in settingIDs) or isCheckoutSetting(themeSetting):
                cleanedSettingsData[themeSetting] = settingsData[themeSetting]
            else:
                print("Theme setting invalid: {0}".format(themeSetting))
    return cleanedSettingsData


def isCheckoutSetting(themeSetting):
    """ Check if setting name begins with "checkout_" """

    try:
        if (themeSetting.index("checkout_") == 0):
            return True
        else:
            return False
    except ValueError:
        return False


def cleanAllSectionSettings(sectionSettings, sectionSchemas, indexSections):
    """Removes all incompatible settings from all sections."""

    cleanedSectionSettings = {}

    for section in sectionSettings:
        print(
            "============\nCLEAN SETTINGS FOR SECTION:\t{0}\n==".format(section))
        if (section in sectionSchemas):
            cleanedSectionSettings[section] = cleanSectionSettings(
                sectionSettings[section], sectionSchemas[section])
        elif (section in indexSections):
            cleanedSectionSettings[section] = sectionSettings[section]
    return cleanedSectionSettings


def cleanSectionSettings(sectionSettings, sectionSchema):
    """Removes section settings from the theme which are not compatible to the section schema."""

    if "blocks" in sectionSettings:
        if "blocks" in sectionSchema:
            sectionSettings["blocks"] = cleanBlocks(
                sectionSettings["blocks"], sectionSchema)
        else:
            sectionSettings.pop("blocks")

    if "settings" in sectionSchema:
        sectionSettings["settings"] = cleanSettings(
            sectionSettings["settings"], sectionSchema["settings"])
            
    return sectionSettings


def cleanSettings(settings, settingsSchema):
    """Removes all settings which are not in the settings schema."""

    cleanedSettings = {}
    for setting in settings:
        if setting in [setting["id"] for setting in settingsSchema if "id" in setting.keys()]:
            cleanedSettings[setting] = settings[setting]
        else:
            print("Setting {0} is not valid!".format(setting))
    return cleanedSettings


def cleanBlocksOrder(blocks, blocks_order):
    """Removes all block IDs from the blocks order which belong to deleted blocks."""

    cleanedBlockOrder = []
    blockIDs = blocks.keys()

    for block in blocks_order:
        if block in blockIDs:
            cleanedBlockOrder.append(block)
    return cleanedBlockOrder


def cleanBlocks(blocks, sectionSchema):
    """Removes all blocks of a section which are not compatible to the section schema."""

    # Create dictionary to store compatible blocks
    cleanedBlocks = {}
    # Loop over all blocks and check if they are valid
    for block in blocks:
        if isBlockValid(blocks[block], sectionSchema):
            # Add valid blocks to the dictionary
            cleanedBlocks[block] = blocks[block]
        else:
            print("Block {0} is not valid!".format(block))
    # Loop over selected blocks and delete obsolete block settings
    for block in cleanedBlocks:
        cleanedBlocks[block]["settings"] = cleanSettings(cleanedBlocks[block]["settings"], getBlockSchema(
            cleanedBlocks[block]["type"], sectionSchema["blocks"])["settings"])

    return cleanedBlocks


def getBlockSchema(blockType, blockSchemas):
    """Retrieve block schema from a list of schemas for a block."""

    for schema in blockSchemas:
        if blockType == schema["type"]:
            return schema


def isBlockValid(block, sectionSchema):
    """Runs several checks on a block to determine whether it fits the schema, defined by the section."""

    try:
        checkIfBlockTypeExists(block, sectionSchema)
        return True
    except BlockUnvalid:
        return False


def checkIfBlockTypeExists(block, sectionSchema):
    """Checks if the type of a block exists in the block types defines by the section."""

    if block["type"] in [block["type"] for block in sectionSchema["blocks"]]:
        return True
    else:
        raise BlockUnvalid("Block is not valid.")


if __name__ == "__main__":
    main()
