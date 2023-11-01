# belongs to other project

from lists import lists
import streamlit as st
import math
import random
import pandas as pd
from itertools import combinations
import os
import time
import json


def is_power_of_two(n):
    if n <= 0:
        return False
    while n > 1:
        if n % 2 != 0:
            return False
        n = n // 2
    return True



def caption(s, stages):
    if s == stages-1:
        return "Final"
    elif s == stages-2:
        return "Semi-Final"
    else:
        return "Round of best "+str(stages**2-s**2)



def calculate_group_stage_parameters(participants, size):
    a = 0
    b = 0

    while size>1:
        x = math.floor(participants/size)
        y = math.floor(participants/(size-1))
        for i in range(0,x):
            for j in range(0,y):
                if i*size+j*(size-1) == participants:
                    a = i
                    b = j
                    return a, b, size
        size -= 1



def shuffle_or_set(participants):
    random.shuffle(participants)



def create_groups(participants: list, max_group_size: int, playoff_size: int):
    if playoff_size > len(participants):
        st.error("Playoff Size larger than participants")

    a, b, size =  calculate_group_stage_parameters(len(participants), max_group_size)
    st.info(f"Created {a} groups of size {size} and {b} groups of size {size-1}")
    # Ensure that the participants list is shuffled to distribute them randomly among groups
    shuffle_or_set(participants)
    # Create and populate the groups
    group_list = []
    idx = 0
    for _ in range(a):
        group = []
        for _ in range(size):
            group.append(participants[idx])
            idx += 1
        group_list.append(group)
    for _ in range(b):
        group = []
        for _ in range(size-1):
            group.append(participants[idx])
            idx += 1
        group_list.append(group)
    for i, group in enumerate(group_list):
        st.session_state["df"][str(i)] = pd.DataFrame({"Teams": group, "Points": [0 for x in range(len(group))]})
    return group_list



def write_results(input, mode: str):
    '''
    returns pandas dataframe for results of ranking
    '''
    results = st.session_state["results"]
    print(results.head())
    
    if mode == "group stage":
        assert type(input) == pd.DataFrame
        results = input
        results = results.sort_values("Points", ascending=False)
    if mode == "playoffs":
        assert type(input) == dict
        for key in input.keys():
            teams_to_update = input[key]
            results[key] = 0
            results[key] = results['Teams'].apply(lambda x: 1 if x in teams_to_update else 0)
    
    sorting_order = ["Points"] + list(input.keys())[::-1]
    results = results.sort_values(sorting_order, ascending=False)
    return results



def group_stage(groups: list):
    st.subheader("Group Stage")
    winners = []
    df_res = pd.DataFrame()
    
    for i, group in enumerate(groups):
        st.text(f"Group {i + 1}")
        res = {}

        for match in list(combinations(group, 2)):
            res[str(match[0])+str(match[1])] = st.selectbox(str(match), options=[match[0], match[1]])
        
        # check if group was already checked
        if i in st.session_state['cg']:
            disabled = True
        else:
            disabled = False

        if st.button("Save "+str(i), disabled=disabled): 
            st.session_state["cg"].add(i)
            for val in res.values():
                if (st.session_state["df"][str(i)]['Teams'] == val).sum() == 1:
                    # Find the row where the 'Teams' column matches the val
                    index = st.session_state["df"][str(i)][st.session_state["df"][str(i)]['Teams'] == val].index[0]
                    # Add 3 to the 'points' column for that row
                    st.session_state["df"][str(i)].iloc[index, 1] += 3 / (len(group)-1)
        st.session_state["df"][str(i)] = st.session_state["df"][str(i)].sort_values("Points", ascending=False)
        st.dataframe(st.session_state["df"][str(i)])
    
    if st.button("Completed"):
        if len(st.session_state["cg"]) != len(groups):
            st.warning("You need to complete every group first")
        else:
            df_res = pd.concat(st.session_state["df"].values(), ignore_index=True)
            df_res = df_res.sort_values("Points", ascending=False)
            st.dataframe(df_res)
            winners = list(df_res['Teams'].iloc[:st.session_state["bo"]])
            st.session_state["stage"] = 3
            st.session_state["participants"] = winners
            st.session_state["results"] = write_results(df_res, "group stage")
    
    if st.button("Skip for Debugging"):
        for group in groups:
            st.session_state["df"][str(group)] = pd.DataFrame({"Teams": group, "Points": [0 for x in range(len(group))]})
        df_res = pd.concat(st.session_state["df"].values(), ignore_index=True)
        df_res = df_res.sort_values("Points", ascending=False)
        st.dataframe(df_res)
        winners = list(df_res['Teams'].iloc[:st.session_state["bo"]])
        st.session_state["stage"] = 3
        st.session_state["participants"] = winners
        st.session_state["results"] = write_results(df_res, "group stage")
        


def playoffs():
    participants = st.session_state["participants"]
    # sort participants according to "strongest vs. weakest"
    participants = [participants[i] for i in range(0, len(participants), 2)] + [participants[i] for i in range(1, len(participants), 2)]
    
    st.subheader("Playoff Stage")

    assert is_power_of_two(len(participants))
    stages = int(math.log2(len(participants)))
    results = {"0": participants}
    winner = {}

    cols = st.columns(stages)

    part = participants
    #random.shuffle(part)
    for s, x in enumerate(cols):
        x.text(caption(s, stages))
        for i in range(0, len(part), 2):
            winner[str(s)+str(i)] = x.radio(str("Game"+str(s)+str(i)), [part[i], part[i+1]])
        if len(winner.keys()) == len(part)/2:
            part = []
            for key in winner.keys():
                part.append(winner[key])
            winner = {}
            results[str(s+1)] = part
    
    if st.button("Finished"):
        st.session_state["results"] = write_results(results, "playoffs")
        st.session_state["stage"] = 4
        st.experimental_rerun()



def save_results():
    key = st.session_state["selected_list"]
    if key in st.session_state["historic_results"].keys():
        df1 = st.session_state["historic_results"][key]
        df2 = st.session_state["results"]
        combined_df = pd.concat([df1, df2], ignore_index=True)
        st.session_state["historic_results"][key] = combined_df.groupby('Teams', as_index=False).sum()
        data_serializable = {key: df.to_dict(orient='records') for key, df in st.session_state["historic_results"].items()}
    else:
        st.session_state["results"]["rounds"] = 1
        st.session_state["historic_results"][key] = st.session_state["results"]
        data_serializable = {key: df.to_dict(orient='records') for key, df in st.session_state["historic_results"].items()}
    with open("saved_results.json", 'w') as file:
        json.dump(data_serializable, file)
    return



def show_results():
    st.subheader("Results of the Ranking")
    st.dataframe(st.session_state["results"])

    # show results
    if st.button("Save results"):
        if not st.session_state["saved_results"]:
            save_results()
            st.info("Successfully saved results")
            st.session_state["saved_results"] = True
        else:
            st.info("Your results were already saved")
    # start another round
    if st.button("Start again"):
        if not st.session_state["saved_results"]:
            st.warning("You have not saved your results yet.")
            if st.button("Continue anyways?"):
                st.session_state["stage"] = 0
            elif st.button("Save first"):
                save_results()
                st.info("Successfully saved results")
        else:
            st.session_state["stage"] = 0



def show_historic_results():
    if not st.session_state["historic_key"] in st.session_state["historic_results"].keys():
        st.error("Could not find list in saved results")
    else:
        df = st.session_state["historic_results"][st.session_state["historic_key"]]
        sorted_cols = [str(i) for i in range(len(df.columns) - 4, 0, -1)]
        # Sort the DataFrame by the selected columns
        sorted_df = df.sort_values(sorted_cols, ascending=False)
        st.dataframe(sorted_df)
    if st.button("Return"):
        st.session_state["stage"] == 0
        return





st.title("Ranking Arena")

if not "stage" in st.session_state:
    st.session_state["stage"] = 0
if not "selected_list" in st.session_state:
    st.session_state["selected_list"] = "debug"
if not "gm" in st.session_state:
    st.session_state["gm"] = 0
if not "bo" in st.session_state:
    st.session_state["bo"] = 0
if not "groups" in st.session_state:
    st.session_state["groups"] = 0
if not "participants" in st.session_state:
    st.session_state["participants"] = list(range(0,31))
if not "results" in st.session_state:
    st.session_state["results"] = pd.DataFrame({"Teams:": st.session_state["participants"]})
if not "cg" in st.session_state:
    st.session_state["cg"] = set()
if not "df" in st.session_state:
    st.session_state["df"] = {}
if not "gs_winners" in st.session_state:
    st.session_state["gs_winners"] = []
if not "saved_results" in st.session_state:
    st.session_state["saved_results"] = False
if not "historic_results" in st.session_state:
    with open('saved_results.json', 'r') as file:
        aux = json.load(file)
        st.session_state["historic_results"] = {key: pd.DataFrame.from_records(data) for key, data in aux.items()}
if not "historic_key" in st.session_state:
    st.session_state["historic_key"] = ""


print("State: ", st.session_state["stage"])
# Load the selected list
if st.session_state["stage"] == 0:
    # Get a list of available list files in the "data" directory
    selected_list = st.selectbox("Select a list to load", lists.keys())
    if st.button("Load"):
        st.session_state["selected_list"] = selected_list
        st.session_state["participants"] = lists[selected_list]
        st.info(f"You successfully loaded list {selected_list}")
        st.session_state["stage"] = 0.5
        st.experimental_rerun()
    # select historic data
    lists_to_choose = st.selectbox("Select a list to show their historic results", st.session_state["historic_results"].keys())
    if st.button("Show results"):
        st.session_state["historic_key"] = lists_to_choose
        st.session_state["stage"] = 5
        st.experimental_rerun()
if st.session_state["stage"] == 0.5:
    # select group stage
    gs = st.radio("Group Stage?", [True, False])
    if gs:
        st.session_state["gm"] = st.select_slider("max members of a group:" , range(3,5))
        st.session_state["bo"] = st.select_slider("Playoff bracket: How many players?" , [2**i for i in range(2, int(math.floor(math.log2(len(st.session_state["participants"])))) + 1)])
    if st.button("Start"):
        if gs:
            st.session_state["stage"] = 1
        else:
            if is_power_of_two(len(st.session_state["participants"])):
                st.session_state["stage"] = 3
                st.experimental_rerun()
            else:
                no = len(st.session_state["participants"])
                st.error(f"The number of particpants ({no}) is no power of 2! Please select a group stage instead.")
if st.session_state["stage"] == 1:
    st.session_state["groups"] = create_groups(st.session_state["participants"], st.session_state["bo"], st.session_state["gm"])
    st.session_state["stage"] = 2
    st.experimental_rerun()
if st.session_state["stage"] == 2:
    group_stage(st.session_state["groups"])
if st.session_state["stage"] == 3:
    playoffs()
if st.session_state["stage"] == 4:
    show_results()
if st.session_state["stage"] == 5:
    show_historic_results()
    