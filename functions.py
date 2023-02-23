import random

items=['planks', 'planks', 'planks', 'planks', 'planks', 'planks', 'book', 'book', 'book']

rewards_map = {'pumpkin': -5, 'egg': -25, 'sugar': -10,
               'pumpkin_pie': 100, 'pumpkin_seeds': -50}

food_recipes = {'pumpkin_pie': ['pumpkin', 'egg', 'sugar'],
                'pumpkin_seeds': ['pumpkin']}

def is_solution(reward):
    return reward == 0

def get_curr_state(items):
    item_keys = []
    for item, quantity in items:
        for i in range(quantity):
            item_keys.append(item)
    item_keys.sort()
    return tuple(item_keys)

def choose_action(curr_state, possible_actions, eps, q_table):
    rnd = random.random()
    if rnd > eps:
        #exploit
        action_q = list(q_table[curr_state].items())
        exploit_action = action_q[0][0]
        max_q = action_q[0][1]
        for action, q_val in action_q:
            if q_val > max_q:
                exploit_action = action
                max_q = q_val
        return exploit_action
    else:
        #explore
        a = random.randint(0, len(possible_actions) - 1)
        return possible_actions[a]