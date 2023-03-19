import sc2
import openai
import re
import random
from sc2 import maps
from sc2.ids.unit_typeid import UnitTypeId
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2.bot_ai import BotAI
from sc2.units import Units
from sc2.unit import Unit


""" WARNING : Python 3.10 required (match/case) """

"""
This project's goal is to see how good a Large Language Model can play StarCraft II on a macro scale, without any fine-
tuning. This python script launches a 1v1 game on the map "Abyssal Reef" against an in-game AI. Observations are made
about the game and a list of possible actions is generated. This data is then sent to ChatGPT using OpenAI's API.
The answer is parsed into its number and reasoning. The number is mapped to its corresponding hardcoded set of actions.
The reasoning is sent to SC2's chat.
"""


# Modify this to match your config. You can also use environment variables instead, but they are broken in my setup lol
openai.api_key_path = "openai.txt"


class ChatGPTAgent(BotAI):
    """Can ChatGPT play StarCraft II in real time ?!"""

    def __init__(self):
        self.action_list = []

    def add_action(self, prompt, name):
        prompt.addAction(name)
        self.action_list.append(name)

    async def on_start(self):
        self.client.game_step = 22 * 15

    async def on_step(self, iteration: int):

        #############
        # Resets

        self.action_list = []
        CCs: Units = self.townhalls(UnitTypeId.COMMANDCENTER)
        cc: Unit = CCs.first
        await self.distribute_workers()  # Replace workers

        #############
        # Misc
        if iteration == 0:
            await self.client.chat_send(
                "Hey ! I am GPTStar, a StarCraft II player powered by ChatGPT. Good luck and have fun !",
                team_only=False)

        # Make a joke sometimes :)
        if random.random() < 1:
            prompt = [{"role": "user", "content": "Make a StarCraft II joke"}]
            answer = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                  messages=[{"role": "user", "content": "Make a StarCraft II joke"}])
            await self.client.chat_send(answer.choices[0].message.content, team_only=False)

        #############
        # ChatGPT
        prompt = Prompt()

        # Ally observation
        prompt.addObservation("game time", self.time_formatted)
        prompt.addObservation("minerals", self.minerals)
        prompt.addObservation("vespene", self.vespene)
        prompt.addObservation("army count", self.supply_army)
        prompt.addObservation("worker count", self.supply_workers)
        prompt.addObservation("supply cap", self.supply_cap)
        prompt.addObservation("number of supply depots", self.structures(UnitTypeId.SUPPLYDEPOT).amount)
        prompt.addObservation("supply depots under construction", self.already_pending(UnitTypeId.SUPPLYDEPOT))
        prompt.addObservation("number of barracks", self.structures(UnitTypeId.BARRACKS).amount)
        prompt.addObservation("number of barracks under construction", self.already_pending(UnitTypeId.BARRACKS))

        """
        # EXPERIMENTAL : GPT 4 GENERATED
        prompt.addObservation("number of factories", self.structures(UnitTypeId.FACTORY).amount)
        prompt.addObservation("number of factories under construction", self.already_pending(UnitTypeId.FACTORY))
        prompt.addObservation("number of starports", self.structures(UnitTypeId.STARPORT).amount)
        prompt.addObservation("number of starports under construction", self.already_pending(UnitTypeId.STARPORT))
        prompt.addObservation("number of command centers", self.structures(UnitTypeId.COMMANDCENTER).amount)
        prompt.addObservation("number of command centers under construction", self.already_pending(UnitTypeId.COMMANDCENTER))
        prompt.addObservation("number of upgrades researched", self.get_researched_upgrades_count())
        """

        # Enemy observation
        prompt.addObservation("enemy units in vision range", self.enemy_units.amount)
        prompt.addObservation("enemy structures in vision range", self.enemy_structures.amount)

        """
        # EXPERIMENTAL : GPT 4 GENERATED
        prompt.addObservation("enemy race", self.enemy_race)
        prompt.addObservation("enemy supply cap", self.enemy_supply_cap)
        prompt.addObservation("enemy army count", self.enemy_supply_army)
        prompt.addObservation("enemy worker count", self.enemy_supply_workers)
        """

        # Possible actions
        self.add_action(prompt, "wait")
        self.add_action(prompt, "train a worker")
        self.add_action(prompt, "build supply depot")
        self.add_action(prompt, "build barracks")
        self.add_action(prompt, "attack enemy base")

        """
        # EXPERIMENTAL : GPT 4 GENERATED
        self.add_action(prompt, "expand to a new base")
        self.add_action(prompt, "build factory")
        self.add_action(prompt, "build starport")
        self.add_action(prompt, "research upgrades")
        self.add_action(prompt, "train marines")
        self.add_action(prompt, "train marauders")
        self.add_action(prompt, "train siege tanks")
        self.add_action(prompt, "train medivacs")
        self.add_action(prompt, "train vikings")
        self.add_action(prompt, "train banshees")
        self.add_action(prompt, "train battlecruisers")
        self.add_action(prompt, "scout enemy base")
        self.add_action(prompt, "defend against enemy attack")
        self.add_action(prompt, "harass enemy economy")
        """

        # Final prompt
        final_prompt = prompt.returnPrompt()
        print("\nPrompt :", final_prompt[1]['content'])

        # ChatGPT API call
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=final_prompt, temperature=1.)

        # ChatGPT's answer as a string
        answer = completion.choices[0].message.content
        print("ChatGPT's answer :", answer)

        # Analyze answer
        chosen_action, reasoning = answer_parser(answer)
        print("Detected action :", self.action_list[chosen_action])

        # Send reasoning in the chat
        await self.client.chat_send(reasoning, team_only=False)

        # Match the textual chosen action with its corresponding set of hard coded actions
        match self.action_list[chosen_action]:

            case "wait":
                pass

            case "train a worker":
                self.train(UnitTypeId.SCV, amount=1)

            case "build supply depot":
                worker = self.workers.random_or(None)
                if worker:
                    await self.build(UnitTypeId.SUPPLYDEPOT,
                                     near=cc.position.towards(self.game_info.map_center), max_distance=20,
                                     build_worker=worker)

            case "build barracks":
                worker = self.workers.random_or(None)
                if worker:
                    barracks_placement_position = self.main_base_ramp.barracks_correct_placement
                    if worker and self.can_afford(UnitTypeId.BARRACKS):
                        worker.build(UnitTypeId.BARRACKS, barracks_placement_position)

            case "attack enemy base":
                for unit in self.units:
                    if not unit.is_structure and not unit in self.workers:
                        unit.attack(self.enemy_start_locations[0])

                """
            # EXPERIMENTAL : GPT 4 GENERATED
                
            case "expand to a new base":
                worker = self.workers.random_or(None)
                if worker:
                    location = await self.get_next_expansion()
                    if location:
                        await self.build(UnitTypeId.COMMANDCENTER, location, build_worker=worker)
    
            case "build factory":
                worker = self.workers.random_or(None)
                if worker:
                    await self.build(UnitTypeId.FACTORY, near=cc.position.towards(self.game_info.map_center), max_distance=20, build_worker=worker)
        
            case "build starport":
                worker = self.workers.random_or(None)
                if worker:
                    await self.build(UnitTypeId.STARPORT, near=cc.position.towards(self.game_info.map_center), max_distance=20, build_worker=worker)
        
            case "research upgrades":
                engineering_bays = self.structures(UnitTypeId.ENGINEERINGBAY).ready
                if engineering_bays.exists:
                    for eb in engineering_bays:
                        if eb.is_idle and self.can_afford(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1):
                            eb.research(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
        
            case "train marines":
                barracks = self.structures(UnitTypeId.BARRACKS).ready.idle
                if barracks.exists:
                    for br in barracks:
                        br.train(UnitTypeId.MARINE)
        
            case "train marauders":
                barracks = self.structures(UnitTypeId.BARRACKS).ready.idle
                if barracks.exists:
                    for br in barracks:
                        br.train(UnitTypeId.MARAUDER)
        
            # Add other unit training and action cases here...
        
            case "scout enemy base":
                scv_scout = self.workers.random_or(None)
                if scv_scout:
                    scv_scout.move(self.enemy_start_locations[0])
        
            case "defend against enemy attack":
                for unit in self.units:
                    if not unit.is_structure and not unit in self.workers:
                        unit.attack(self.closest_enemy_unit(unit).position)
        
            case "harass enemy economy":
                harass_units = self.units.filter(lambda u: u.type_id in {UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.HELLION} and u.is_idle)
                if harass_units.exists:
                    target = self.closest_enemy_worker(harass_units.first)
                    if target:
                        harass_units.attack(target)
                """


class Prompt:
    """
    Generates a new prompt to send to ChatGPT.
    Example :
    Observations : minerals:99, vespene:54. Actions : 1) attack, 2) defend.
    """

    def __init__(self):
        self.systemPrompt = "You are GPTStar, a professional StarCraft II player. " \
                            "Your assistant gives you a detailed list of features about " \
                            "the game they can see on your screen. They then give you a " \
                            "list of numbered actions you can currently do. You answer " \
                            "with the number of the action you choose followed by a short " \
                            "phrase explaining your reasoning."

        self.obsPrompt = "Observations : "
        self.actionPrompt = "Possible Actions :"
        self.actionCount = 0

    # Adds an observation to the final prompt
    def addObservation(self, name: str, value: int | float | str):
        self.obsPrompt += name + " is " + str(value) + ", "

    # Adds an action to the final prompt. Keeps track of the action number, so you don't have to.
    def addAction(self, name: str):
        self.actionPrompt += str(self.actionCount) + ") " + name + ". "
        self.actionCount += 1

    # Returns an API-ready prompt
    def returnPrompt(self):
        messages = [{"role": "system", "content": self.systemPrompt},
                    {"role": "user", "content": self.obsPrompt.rstrip(", ") + ". " + self.actionPrompt}]
        return messages


# Translates ChatGPT's answer. Returns the number of its action and its reasoning
def answer_parser(answer: str):
    chosen_action = re.search(r'[0-9]+', answer)
    reasoning = ""
    sentences = answer.split(".")
    for i in range(1, len(sentences) - 1):
        reasoning += sentences[i] + "."
    return int(chosen_action.group()), reasoning.lstrip(" ")


# Launches the game :)
run_game(
    sc2.maps.get("AbyssalReefLE"),
    [Bot(Race.Terran, ChatGPTAgent()), Computer(Race.Zerg, Difficulty.Easy)],
    realtime=True,
)
