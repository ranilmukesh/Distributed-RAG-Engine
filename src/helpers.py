import copy
import datetime
import pandas as pd
import uuid
import datetime
from typing import List
import os
import logging


def init_session_1(st, ss, col1, col2):
    """
    initialize session state for multiple files option
    param: st  session
    param: ss  session state
    param: model  chat (gemini model)
    """

    if "chat_history1" not in st.session_state:
        st.session_state["chat_history1"] = []
    if "data1" not in st.session_state:
        st.session_state["data1"] = []
    if "vector_store1" not in st.session_state:
        st.session_state["vector_store1"] = None
    if "retriever1" not in st.session_state:
        st.session_state["retriever1"] = None
    if "llamaindex1" not in st.session_state:
        st.session_state["llamaindex1"] = None
    # placeholder for multiple files
    if "file_name1" not in st.session_state:
        st.session_state["file_name1"] = "no file"
    if "upload_state1" not in st.session_state:
        st.session_state["upload_state1"] = ""
    if "file_history1" not in st.session_state:
        st.session_state["file_history1"] = "no file"
    if "prompt_introduced1" not in st.session_state:
        st.session_state["prompt_introduced1"] = ""
    if "chat_true1" not in st.session_state:
        st.session_state["chat_true1"] = "no_chat"
    if "pdf_ref1" not in ss:
        ss.pdf_ref1 = None
    if "value1" not in st.session_state:
        st.session_state.value1 = 0
    # buttom send to gemini
    if "vcol1doc" not in st.session_state:
        st.session_state["vcol1doc"] = col1
    if "vcol2doc" not in st.session_state:
        st.session_state["vcol2doc"] = col2
    if "expander_1" not in st.session_state:
        st.session_state["expander_1"] = True
    if "click_button_parse1" not in st.session_state:
        st.session_state["click_button_parse1"] = False
    st.session_state["init_run_1"] = True
    return


def reset_session_1(st, ss):
    """
    Delete session state for multiple files option
    param: st  session
    param: ss  session state
    param: model  chat (gemini model)
    """

    del st.session_state["chat_history1"]
    del st.session_state["db_local_folder1"]
    del st.session_state["db_local_file1"]
    del st.session_state["chat1"]
    del st.session_state["vector_store1"]
    del st.session_state["embeddings1"]
    del st.session_state["retriever1"]
    # placeholder for multiple files
    del st.session_state["file_name1"]
    del st.session_state["file_history1"]
    del st.session_state["prompt_introduced1"]
    del st.session_state["chat_true1"]
    del ss.pdf_ref1
    del st.session_state.value1
    # buttom send to gemini
    del st.session_state["vcol1doc"]
    del st.session_state["vcol2doc"]
    del st.session_state["expander_1"]
    del st.session_state["init_run_1"]
    # delete objects
    del st.session_state["pdf"]
    del st.session_state["pdf_viewer"]
    del st.session_state["pdf_query"]
    del st.session_state["upload_state1"]
    del st.session_state["click_button_parse1"]
    st.session_state["salir_1"] = False

    return


def save_df_many(list2: List, df: pd.DataFrame, fname: str, prompt: str, filename: str):
    """
    Save prompt to a json file
    :param name_prompt: name of the prompt
    :param prompt: prompt
    :param keywords: keywords
    :param df: dataframe with all prompts
    """
    if len(list2) > 1:
        list2.reverse()
    p_dict = {}
    p_dict["id"] = str(uuid.uuid4())
    p_dict["filename"] = filename
    p_dict["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p_dict["prompt"] = prompt.replace(",", "")
    p_dict["respuesta_chat"] = list2[0].replace(",", "")
    row = pd.DataFrame(p_dict, index=[0])
    df = pd.concat([df, row], ignore_index=True)
    df.to_csv(fname, index=False)

    return


def save_df_pdf(df: pd.DataFrame, fname: str, filename: str):
    """
    Save prompt to a json file
    :param name_prompt: name of the prompt
    :param prompt: prompt
    :param keywords: keywords
    :param df: dataframe with all prompts
    """

    p_dict = {}
    p_dict["id"] = str(uuid.uuid4())
    p_dict["filename"] = filename
    p_dict["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = pd.DataFrame(p_dict, index=[0])
    df = pd.concat([df, row], ignore_index=True)
    df.to_csv(fname, index=False)

    return


def get_filename_multi(st):
    """
    extract filename from multi file name
    """

    text0 = ""
    for file in st.session_state["multi_file_name"]:
        text0 = text0 + file.replace(".pdf", "") + "_"
    filename = text0[:-1]
    return filename


def write_history_1(st, path):
    """
    Write history to file 1 doc
    param: st  session
    """
    text = ""
    list1 = copy.deepcopy(st.session_state["chat_history1"])
    list2 = copy.deepcopy(st.session_state["chat_history1"])

    if len(st.session_state["chat_history1"]) > 1:
        list1.reverse()

    if len(st.session_state["chat_history1"]) > 1:
        list2.reverse()

    for i, j in zip(list1, list2):
        text = text + "user :" + j[0] + "\n"
        text = text + "assistant :" + i[1] + "\n"

    now = datetime.datetime.now()
    now = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(
        path, f"{st.session_state['file_history1']}_{now}_history.txt"
    )
    logging.info(f"writing history to {filename}")
    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(text)
        f.close()
    return
