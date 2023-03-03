"""
Odie is trying to get the best present. Help him to learn what he should do.

Author: Moshe Lichman and Sameer Singh
"""
%load_ext autoreload
%autoreload 2

from __future__ import division
import numpy as np

import malmo.MalmoPython as MalmoPython
import os
import random
import sys
import time
import json
import random
import math
import errno
import assignment2_submission as submission
from collections import defaultdict, deque
from timeit import default_timer as timer

items=submission.items
inventory_limit = 30
food_recipes = submission.food_recipes
rewards_map = submission.rewards_map

def buildPositionList(items):
    """Places the items in a circle."""
    positions = []
    angle = 2*math.pi/len(items)
    for i in range(len(items)):
        item = items[i]
        x = int(6*math.sin(i*angle))
        y = int(6*math.cos(i*angle))
        positions.append((x, y))
    return positions


def getItemDrawing(positions):
    """Create the XML for the items."""
    drawing = ""
    index = 0
    for p in positions:
        item = items[index].split()
        drawing += '<DrawItem x="' + str(p[0]) + '" y="228" z="' + str(p[1]) + '" type="' + item[0]
        if len(item) > 1:
            drawing += '" variant="' + item[1]
        drawing += '" />'
        index += 1
    return drawing


def GetMissionXML(summary):
    ''' Build an XML mission string that uses the RewardForCollectingItem mission handler.'''

    positions = buildPositionList(items)

    return '''<?xml version="1.0" encoding="UTF-8" ?>
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <About>
            <Summary>''' + summary + '''</Summary>
        </About>

        <ModSettings>
            <MsPerTick>100</MsPerTick>
        </ModSettings>

        <ServerSection>
            <ServerInitialConditions>
                <Time>
                    <StartTime>6000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                </Time>
                <Weather>clear</Weather>
                <AllowSpawning>false</AllowSpawning>
            </ServerInitialConditions>
            <ServerHandlers>
                <FlatWorldGenerator generatorString="3;7,220*1,5*3,2;3;,biome_1" />
                <DrawingDecorator>
                    <DrawCuboid x1="-50" y1="226" z1="-50" x2="50" y2="228" z2="50" type="air" />
                    <DrawCuboid x1="-50" y1="226" z1="-50" x2="50" y2="226" z2="50" type="monster_egg" variant="chiseled_brick" />
                    <DrawCuboid x1="-3" y1="226" z1="-3" x2="3" y2="226" z2="3" type="dirt" />
                    <DrawBlock x="-0" y="226" z="0" type="diamond_block"/>
                    ''' + getItemDrawing(positions) + '''
                </DrawingDecorator>
                <ServerQuitWhenAnyAgentFinishes />
            </ServerHandlers>
        </ServerSection>

        <AgentSection mode="Survival">
            <Name>Odie</Name>
            <AgentStart>
                <Placement x="0.5" y="227.0" z="0.5"/>
                <Inventory>
                    <InventoryItem slot="9" type="planks" variant="oak"/>
                    <InventoryItem slot="10" type="planks" variant="oak"/>
                    <InventoryItem slot="11" type="planks" variant="oak"/>
                    <InventoryItem slot="12" type="planks" variant="oak"/>
                    <InventoryItem slot="13" type="planks" variant="oak"/>
                    <InventoryItem slot="14" type="planks" variant="oak"/>
                    <InventoryItem slot="15" type="book"/>
                    <InventoryItem slot="16" type="book"/>
                    <InventoryItem slot="17" type="book"/>
                </Inventory>
            </AgentStart>
            <AgentHandlers>
                <ContinuousMovementCommands turnSpeedDegs="480"/>
                <AbsoluteMovementCommands/>
                <SimpleCraftCommands/>
                <MissionQuitCommands/>
                <InventoryCommands/>
                <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="40" yrange="40" zrange="40"/>
                </ObservationFromNearbyEntities>
                <ObservationFromFullInventory/>
                <AgentQuitFromCollectingItem>
                    <Item type="rabbit_stew" description="Supper's Up!!"/>
                </AgentQuitFromCollectingItem>
            </AgentHandlers>
        </AgentSection>

    </Mission>'''


class Odie(object):
    def __init__(self, alpha=0.3, gamma=1, n=1):
        """Constructing an RL agent.

        Args
            alpha:  <float>  learning rate      (default = 0.3)
            gamma:  <float>  value decay rate   (default = 1)
            n:      <int>    number of back steps to update (default = 1)
        """
        self.epsilon = 0.2  # chance of taking a random action instead of the best
        self.q_table = {}
        self.n, self.alpha, self.gamma = n, alpha, gamma
        self.inventory = {'planks': 6, 'book': 3}
        self.num_items_in_inv = 9

    def clear_inventory(self):
        self.inventory = {'planks': 6, 'book': 3}
        self.num_items_in_inv = 9
       

    def get_crafting_options(self):
        """Returns the objects that can be crafted from the inventory. """
        import copy
        craft_opt = []
        inventory_items = []
        for item, count in self.inventory.items():
            for j in range(count):
                inventory_items.append(item)

        for item, recipe in food_recipes.items():
            t_inventory_items = copy.deepcopy(inventory_items)
            inter = []
            for i in recipe:
                if i in t_inventory_items:
                    inter.append(i)
                    t_inventory_items.remove(i)
            if len(inter) == len(recipe):
                craft_opt.append(item)
        return craft_opt

    def craft_item(self, agent_host, item):
        items_needed = food_recipes[item]
        for item_needed in items_needed:
            self.inventory[item_needed] -= 1
            self.num_items_in_inv -= 1
            if self.inventory[item_needed] < 0:
                raise AssertionError('Missing items for crafting: %s in %s' % (item_needed, str(self.inventory_items)))

        agent_host.sendCommand('craft %s' % item)
        #self.inventory[item] += 1
        self.inventory[item] = self.inventory.get(item, 0) + 1
        self.num_items_in_inv += 1
        time.sleep(0.25)

    @staticmethod
    def is_solution(reward):
        """If the reward equals to the maximum reward possible returns True, False otherwise. """
        return submission.is_solution(reward)

    def get_possible_actions(self, agent_host, is_first_action=False):
        """Returns all possible actions that can be done at the current state. """
        action_list = []

        craft_opt = self.get_crafting_options()
        if len(craft_opt) > 0:
            action_list.extend(['c_%s' % craft_item for craft_item in craft_opt])
        
        return action_list

    def get_curr_state(self):
        """Creates a unique identifier for a state.

        The state is defined as the items in the agent inventory. Notice that the state has to be sorted -- otherwise
        differnt order in the inventory will be different states.
        """
        return submission.get_curr_state(self.inventory.items())

    def choose_action(self, curr_state, possible_actions, eps):
        """Chooses an action according to eps-greedy policy. """
        if curr_state not in self.q_table:
            self.q_table[curr_state] = {}
        for action in possible_actions:
            if action not in self.q_table[curr_state]:
                self.q_table[curr_state][action] = 0
        if len(possible_actions) == 0:
            print("No possible actions in table.")

        return submission.choose_action(curr_state, possible_actions, eps, self.q_table)

    def act(self, agent_host, action):
        print(action + ",", end = " ")
        if action.startswith('c_'):
            self.craft_item(agent_host, action[2:])
        else:
            print("error")
        print("Reward: " + str(rewards_map[action[2:]]))
        return rewards_map[action[2:]]

    def update_q_table(self, state, action, next_state, reward):
        if state not in self.q_table:
            self.q_table[state] = {}
        if action not in self.q_table[state]:
            self.q_table[state][action] = 0
        if next_state not in self.q_table:
            self.q_table[next_state] = {}
            next_max = 0
        else:
            next_max = max(self.q_table[state].values())
        old_value = self.q_table[state][action]
        new_value = (1 - self.alpha) * old_value + self.alpha * (reward + self.gamma * next_max)
        self.q_table[state, action] = new_value

    def run(self, agent_host):
        done_update = False
        while not done_update:
            odie.clear_inventory()
            s0 = self.get_curr_state()
            possible_actions = self.get_possible_actions(agent_host, True)
            a0 = self.choose_action(s0, possible_actions, self.epsilon)
            
            reward = self.act(agent_host, a0)
            
            next_state = self.get_curr_state()
            if next_state not in self.q_table:
                self.q_table[next_state] = {}
            
            self.update_q_table(s0, a0, next_state, reward)
            if reward == 100:
                done_update = True
                sys.exit()

if __name__ == '__main__':
    random.seed(0)
    #sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
    print('Starting...', flush=True)
    print(items)
    expected_reward = 3390
    my_client_pool = MalmoPython.ClientPool()
    my_client_pool.add(MalmoPython.ClientInfo("127.0.0.1", 10000))
    
    agent_host = MalmoPython.AgentHost()
    try:
        agent_host.parse(sys.argv)
    except RuntimeError as e:
        print('ERROR:', e)
        print(agent_host.getUsage())
        exit(1)
    if agent_host.receivedArgument("help"):
        print(agent_host.getUsage())
        exit(0)

    num_reps = 30000
    n=1
    odie = Odie(n=n)
    print("n=",n)
    odie.clear_inventory()
    for iRepeat in range(num_reps):
        odie.clear_inventory()
        my_mission = MalmoPython.MissionSpec(GetMissionXML("Fetch boy #" + str(iRepeat)), True)
        my_mission_record = MalmoPython.MissionRecordSpec()  # Records nothing by default
        my_mission.requestVideo(800, 500)
        my_mission.setViewpoint(0)
        max_retries = 3
        for retry in range(max_retries):
            try:
                agent_host.startMission(my_mission, my_client_pool, my_mission_record, 0, "Odie")
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print("Error starting mission", e)
                    print("Is the game running?")
                    exit(1)
                else:
                    time.sleep(2)

        world_state = agent_host.getWorldState()
        while not world_state.has_mission_begun:
            time.sleep(0.1)
            world_state = agent_host.getWorldState()
        odie.run(agent_host)

        odie.clear_inventory()
        time.sleep(1)
"""
Odie is trying to get the best present. Help him to learn what he should do.

Author: Moshe Lichman and Sameer Singh
"""
%load_ext autoreload
%autoreload 2

from __future__ import division
import numpy as np

import malmo.MalmoPython as MalmoPython
import os
import random
import sys
import time
import json
import random
import math
import errno
import assignment2_submission as submission
from collections import defaultdict, deque
from timeit import default_timer as timer

items=submission.items
inventory_limit = 30
food_recipes = submission.food_recipes
rewards_map = submission.rewards_map

def buildPositionList(items):
    """Places the items in a circle."""
    positions = []
    angle = 2*math.pi/len(items)
    for i in range(len(items)):
        item = items[i]
        x = int(6*math.sin(i*angle))
        y = int(6*math.cos(i*angle))
        positions.append((x, y))
    return positions


def getItemDrawing(positions):
    """Create the XML for the items."""
    drawing = ""
    index = 0
    for p in positions:
        item = items[index].split()
        drawing += '<DrawItem x="' + str(p[0]) + '" y="228" z="' + str(p[1]) + '" type="' + item[0]
        if len(item) > 1:
            drawing += '" variant="' + item[1]
        drawing += '" />'
        index += 1
    return drawing


def GetMissionXML(summary):
    ''' Build an XML mission string that uses the RewardForCollectingItem mission handler.'''

    positions = buildPositionList(items)

    return '''<?xml version="1.0" encoding="UTF-8" ?>
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <About>
            <Summary>''' + summary + '''</Summary>
        </About>

        <ModSettings>
            <MsPerTick>100</MsPerTick>
        </ModSettings>

        <ServerSection>
            <ServerInitialConditions>
                <Time>
                    <StartTime>6000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                </Time>
                <Weather>clear</Weather>
                <AllowSpawning>false</AllowSpawning>
            </ServerInitialConditions>
            <ServerHandlers>
                <FlatWorldGenerator generatorString="3;7,220*1,5*3,2;3;,biome_1" />
                <DrawingDecorator>
                    <DrawCuboid x1="-50" y1="226" z1="-50" x2="50" y2="228" z2="50" type="air" />
                    <DrawCuboid x1="-50" y1="226" z1="-50" x2="50" y2="226" z2="50" type="monster_egg" variant="chiseled_brick" />
                    <DrawCuboid x1="-3" y1="226" z1="-3" x2="3" y2="226" z2="3" type="dirt" />
                    <DrawBlock x="-0" y="226" z="0" type="diamond_block"/>
                    ''' + getItemDrawing(positions) + '''
                </DrawingDecorator>
                <ServerQuitWhenAnyAgentFinishes />
            </ServerHandlers>
        </ServerSection>

        <AgentSection mode="Survival">
            <Name>Odie</Name>
            <AgentStart>
                <Placement x="0.5" y="227.0" z="0.5"/>
                <Inventory>
                    <InventoryItem slot="9" type="planks" variant="oak"/>
                    <InventoryItem slot="10" type="planks" variant="oak"/>
                    <InventoryItem slot="11" type="planks" variant="oak"/>
                    <InventoryItem slot="12" type="planks" variant="oak"/>
                    <InventoryItem slot="13" type="planks" variant="oak"/>
                    <InventoryItem slot="14" type="planks" variant="oak"/>
                    <InventoryItem slot="15" type="book"/>
                    <InventoryItem slot="16" type="book"/>
                    <InventoryItem slot="17" type="book"/>
                </Inventory>
            </AgentStart>
            <AgentHandlers>
                <ContinuousMovementCommands turnSpeedDegs="480"/>
                <AbsoluteMovementCommands/>
                <SimpleCraftCommands/>
                <MissionQuitCommands/>
                <InventoryCommands/>
                <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="40" yrange="40" zrange="40"/>
                </ObservationFromNearbyEntities>
                <ObservationFromFullInventory/>
                <AgentQuitFromCollectingItem>
                    <Item type="rabbit_stew" description="Supper's Up!!"/>
                </AgentQuitFromCollectingItem>
            </AgentHandlers>
        </AgentSection>

    </Mission>'''


class Odie(object):
    def __init__(self, alpha=0.3, gamma=1, n=1):
        """Constructing an RL agent.

        Args
            alpha:  <float>  learning rate      (default = 0.3)
            gamma:  <float>  value decay rate   (default = 1)
            n:      <int>    number of back steps to update (default = 1)
        """
        self.epsilon = 0.2  # chance of taking a random action instead of the best
        self.q_table = {}
        self.n, self.alpha, self.gamma = n, alpha, gamma
        self.inventory = {'planks': 6, 'book': 3}
        self.num_items_in_inv = 9

    def clear_inventory(self):
        self.inventory = {'planks': 6, 'book': 3}
        self.num_items_in_inv = 9
       

    def get_crafting_options(self):
        """Returns the objects that can be crafted from the inventory. """
        import copy
        craft_opt = []
        inventory_items = []
        for item, count in self.inventory.items():
            for j in range(count):
                inventory_items.append(item)

        for item, recipe in food_recipes.items():
            t_inventory_items = copy.deepcopy(inventory_items)
            inter = []
            for i in recipe:
                if i in t_inventory_items:
                    inter.append(i)
                    t_inventory_items.remove(i)
            if len(inter) == len(recipe):
                craft_opt.append(item)
        return craft_opt

    def craft_item(self, agent_host, item):
        items_needed = food_recipes[item]
        for item_needed in items_needed:
            self.inventory[item_needed] -= 1
            self.num_items_in_inv -= 1
            if self.inventory[item_needed] < 0:
                raise AssertionError('Missing items for crafting: %s in %s' % (item_needed, str(self.inventory_items)))

        agent_host.sendCommand('craft %s' % item)
        #self.inventory[item] += 1
        self.inventory[item] = self.inventory.get(item, 0) + 1
        self.num_items_in_inv += 1
        time.sleep(0.25)

    @staticmethod
    def is_solution(reward):
        """If the reward equals to the maximum reward possible returns True, False otherwise. """
        return submission.is_solution(reward)

    def get_possible_actions(self, agent_host, is_first_action=False):
        """Returns all possible actions that can be done at the current state. """
        action_list = []

        craft_opt = self.get_crafting_options()
        if len(craft_opt) > 0:
            action_list.extend(['c_%s' % craft_item for craft_item in craft_opt])
        
        return action_list

    def get_curr_state(self):
        """Creates a unique identifier for a state.

        The state is defined as the items in the agent inventory. Notice that the state has to be sorted -- otherwise
        differnt order in the inventory will be different states.
        """
        return submission.get_curr_state(self.inventory.items())

    def choose_action(self, curr_state, possible_actions, eps):
        """Chooses an action according to eps-greedy policy. """
        if curr_state not in self.q_table:
            self.q_table[curr_state] = {}
        for action in possible_actions:
            if action not in self.q_table[curr_state]:
                self.q_table[curr_state][action] = 0
        if len(possible_actions) == 0:
            print("No possible actions in table.")

        return submission.choose_action(curr_state, possible_actions, eps, self.q_table)

    def act(self, agent_host, action):
        print(action + ",", end = " ")
        if action.startswith('c_'):
            self.craft_item(agent_host, action[2:])
        else:
            print("error")
        print("Reward: " + str(rewards_map[action[2:]]))
        return rewards_map[action[2:]]

    def update_q_table(self, state, action, next_state, reward):
        if state not in self.q_table:
            self.q_table[state] = {}
        if action not in self.q_table[state]:
            self.q_table[state][action] = 0
        if next_state not in self.q_table:
            self.q_table[next_state] = {}
            next_max = 0
        else:
            next_max = max(self.q_table[state].values())
        old_value = self.q_table[state][action]
        new_value = (1 - self.alpha) * old_value + self.alpha * (reward + self.gamma * next_max)
        self.q_table[state, action] = new_value

    def run(self, agent_host):
        done_update = False
        while not done_update:
            odie.clear_inventory()
            s0 = self.get_curr_state()
            possible_actions = self.get_possible_actions(agent_host, True)
            a0 = self.choose_action(s0, possible_actions, self.epsilon)
            
            reward = self.act(agent_host, a0)
            
            next_state = self.get_curr_state()
            if next_state not in self.q_table:
                self.q_table[next_state] = {}
            
            self.update_q_table(s0, a0, next_state, reward)
            if reward == 100:
                done_update = True
                sys.exit()

if __name__ == '__main__':
    random.seed(0)
    #sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
    print('Starting...', flush=True)
    print(items)
    expected_reward = 3390
    my_client_pool = MalmoPython.ClientPool()
    my_client_pool.add(MalmoPython.ClientInfo("127.0.0.1", 10000))
    
    agent_host = MalmoPython.AgentHost()
    try:
        agent_host.parse(sys.argv)
    except RuntimeError as e:
        print('ERROR:', e)
        print(agent_host.getUsage())
        exit(1)
    if agent_host.receivedArgument("help"):
        print(agent_host.getUsage())
        exit(0)

    num_reps = 30000
    n=1
    odie = Odie(n=n)
    print("n=",n)
    odie.clear_inventory()
    for iRepeat in range(num_reps):
        odie.clear_inventory()
        my_mission = MalmoPython.MissionSpec(GetMissionXML("Fetch boy #" + str(iRepeat)), True)
        my_mission_record = MalmoPython.MissionRecordSpec()  # Records nothing by default
        my_mission.requestVideo(800, 500)
        my_mission.setViewpoint(0)
        max_retries = 3
        for retry in range(max_retries):
            try:
                agent_host.startMission(my_mission, my_client_pool, my_mission_record, 0, "Odie")
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print("Error starting mission", e)
                    print("Is the game running?")
                    exit(1)
                else:
                    time.sleep(2)

        world_state = agent_host.getWorldState()
        while not world_state.has_mission_begun:
            time.sleep(0.1)
            world_state = agent_host.getWorldState()
        odie.run(agent_host)

        odie.clear_inventory()
        time.sleep(1)
