
import random
import gym
import make_env_
import numpy as np
import csv
# from collections import deque
import tensorflow as tf
import os  # for creating directories

from DPG import PolicyGradientAgent  # PG agent

np.random.seed(1)
tf.set_random_seed(1)

# ^ Set parameters

env = make_env_.make_env('traffic', benchmark=True)

num_of_agents = env.n
num_of_walls = len(env.world.landmarks)

state_size = 2+2+2+4 
# [agent's velocity(2d vector) + agent's position(2d vector) +
# agent's destination(2d vector)
# sensor values (4d vector) +



action_size = 5  # discrete action space [up,down,left,right,dont move]

testing = True  # render in testing
render = True

n_episodes = 10 if  testing else 100000  # number of simulations
n_steps = 300 if testing else 300  # number of steps

saving_freq = 1000

load_episode = 5000
 
output_dir = 'model_output/traffic/DPG_5v5_v3'

# # ────────────────────────────────────────────────────────────────────────────────
# if testing:
#     import pyautogui
#  ────────────────────────────────────────────────────────────────────────────────


# ^ Interact with environment

agents = [PolicyGradientAgent(state_size, action_size, env.agents[agent])
          for agent in range(num_of_agents)]  # initialize agents

#! create model output folders
for i, agent in enumerate(agents):
    if not os.path.exists(output_dir + "/weights/agent{}".format(i)):
        os.makedirs(output_dir + "/weights/agent{}".format(i))

#! load weights if exist
for i, agent in enumerate(agents):
    file_name = (output_dir + "/weights/agent{}/".format(i) +
                 "weights_" + '{:04d}'.format(load_episode))
    try:
        agent.load(file_name)
        print("Loaded weights to use for agent {}".format(i))
    except:
        print("No weights to use for agent {}".format(i))
    finally:
        pass

#! statistics
# ────────────────────────────────────────────────────────────────────────────────
collision_ = ['collision_{}'.format(i) for i in range(num_of_agents)]
loss_ = ['loss_{}'.format(i) for i in range(num_of_agents)]
reward_ = ['reward_{}'.format(i) for i in range(num_of_agents)]
statistics = ['episode']+collision_+reward_+loss_

if not testing:
    with open(output_dir + '/statistics.csv', 'a') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(statistics)
    csvFile.close()
# ────────────────────────────────────────────────────────────────────────────────

for episode in range(1, n_episodes+1):  # iterate over new episodes of the game
    # if(episode % 500 == 0):
    #     n_steps += 50
    # ────────────────────────────────────────────────────────────────────────────────
    # ^ for statistics
    statictics_row = []
    collisions = [0]*num_of_agents
    rewards_ = [0]*num_of_agents
    losses = [0]*num_of_agents
    # ────────────────────────────────────────────────────────────────────────────────

    states = env.reset()  # reset states at start of each new episode of the game

    for step in range(1, n_steps+1):  # for every step
        #* if all the agents reached the destination or Wreck pass to the next episode
        if all([agent.gym_agent.isDone or agent.gym_agent.isWreck for agent in agents]):
            break

        if (render):
            env.render()

        all_actions = []
        all_actions_index = []
        for state, agent in zip(states, agents):
            
            if agent.gym_agent.isDone or agent.gym_agent.isWreck:
                all_actions.append(np.array([1,0,0,0,0]))
                all_actions_index.append(0)
            else:
                act_index = agent.act(state)
                all_actions_index.append(act_index)
                onehot_action = np.zeros(action_size)
                onehot_action[act_index] = 1
                all_actions.append(onehot_action)
            
        next_states, rewards, dones, infos = env.step(
            all_actions)  # take a step (update all agents)

        # ─────────────────────────────────────────────────────────────────
        #* collision,reward statistics
        for i in range(num_of_agents):
            collisions[i] += (infos['collision'][i])
            rewards_[i] += (rewards[i])
        # ────────────────────────────────────────────────────────────────────────────────

        # for state in next_states:
        #     state = np.reshape(state, [1, state_size]) #! reshape the state for DQN model

        for i, agent in enumerate(agents):
            #! dont use the steps after isDone or isWreck 
            if agent.gym_agent.isWreck_ or agent.gym_agent.isDone_:
                continue
            agent.remember(states[i], all_actions_index[i], rewards[i])
            # remember the previous timestep's state, actions, reward vs.

        states = next_states  # update the states

    # End of the episode
    for i, agent in enumerate(agents):

        rewards_sum = sum(agent.rewards)

        if 'running_reward' not in globals():
            running_reward = rewards_sum
        else:
            running_reward = running_reward * \
                agent.gamma + rewards_sum * (1-agent.gamma)

        value, loss = agent.learn()

        losses[i] = loss
    # ────────────────────────────────────────────────────────────────────────────────

    print("\n episode: {}/{}, \
    collisions: {}|{}|{}|{}|{}|{} \
    rewards: {:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}, \
    losses: {:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}|{:.2f}".format(episode,
                                         n_episodes,
                                         collisions[0],
                                         collisions[1],
                                         collisions[2],
                                         collisions[-3],
                                         collisions[-2],
                                         collisions[-1],
                                         rewards_[0],
                                         rewards_[1],
                                         rewards_[2],
                                         rewards_[-3],
                                         rewards_[-2],
                                         rewards_[-1],
                                         losses[0],
                                         losses[1],
                                         losses[2],
                                         losses[-3],
                                         losses[-2],
                                         losses[-1]))

    #! episode,collisions,rewards,losses statistics written
    statictics_row.append(episode)
    statictics_row += (collisions)
    statictics_row += (rewards_)
    statictics_row += (losses)

    if not testing:
        with open(output_dir + '/statistics.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(statictics_row)
        csvFile.close()

    # ────────────────────────────────────────────────────────────────────────────────
    #! save weights
    if not testing:
        if episode % saving_freq == 0:
            for i, agent in enumerate(agents):
                agent.save(output_dir + "/weights/agent{}/".format(i) +
                           "weights_" + '{:04d}'.format(episode))
