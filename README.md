
# GPTStar

Can ChatGPT play StarCraft II in real time ?

## Introduction
This project's goal is to see how good a Large Language Model can play StarCraft II on a macro scale, without any fine-tuning.

Observations are made about the game and a list of possible actions is generated. This data is then sent to ChatGPT using OpenAI's API.  The answer is parsed into its number and reasoning. The number is mapped to its corresponding hardcoded set of actions.  The reasoning is sent to SC2's chat.

Here is a [video example](https://streamable.com/od2bpx) of ChatGPT performing basic actions.

GPT-3.5 is a very strange player : it loves supply depots ! GPT-4's game sense is sharper but I don't have an API key for it yet...


## How to...
### Install the maps
Follow [this guide](https://github.com/Blizzard/s2client-proto#downloads) to install the maps. Abyssal Reef is in the 2017 season 1 pack. 
### Get an OpenAI API key
You need an API key in order to make requests to ChatGPT.
Register an account on [OpenAI's website](https://platform.openai.com/). You can generate new keys on [this page](https://platform.openai.com/account/api-keys). **API keys are secret, don't share them !**