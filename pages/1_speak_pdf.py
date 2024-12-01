import streamlit as st
import os.path
from streamlit_pdf_viewer import pdf_viewer
from streamlit import session_state as ss
from pathlib import Path
from dotenv import dotenv_values
import json
import logging
from src.utils import print_stack
from src.pdf_utils import count_pdf_pages, docs_from_pymupdf4llm
from src.helpers import init_session_1, reset_session_1, write_history_1
from src.work_nvidia import (
    get_llm,
    get_embeddings,
    vectorindex_from_data,
    create_chat_engine,
    setup_index,
)
from src.vector import load_index_from_disk, persist_index_to_disk
from IPython import embed
from src.distributed_processor import DistributedPDFProcessor


# where I am
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
path = Path(ROOT_DIR)
TMP_FOLDER = os.path.join(path.parent.absolute(), "tmp")
# Create folders
logging.info(f"Root Dir {ROOT_DIR} Temp Folder {TMP_FOLDER}")


def change_state_1(st, placeholder):
    if len(st.session_state["chat_history1"]) > 1:
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        path = Path(ROOT_DIR)
        ANSWERS_FOLDER = os.path.join(path.parent.absolute(), "answers")
        logging.info("Salir and writing history")
        write_history_1(st, path=ANSWERS_FOLDER)

    placeholder.empty()
    reset_session_1(st, ss)
    st.stop()
    del placeholder

    return


def click_button_parse(st):
    st.session_state["click_button_parse1"] = True
    return


def model_selector():
    with st.sidebar:
        provider = st.selectbox(
            "Select LLM Provider",
            ["openai", "claude", "azure"],
            key="llm_provider"
        )
        
        if provider == "openai":
            model = st.selectbox(
                "Select Model",
                ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
                key="openai_model"
            )
        elif provider == "claude":
            model = st.selectbox(
                "Select Model",
                ["claude-3-sonnet-20240229", "claude-3-opus-20240229"],
                key="claude_model"
            )
        elif provider == "azure":
            model = st.text_input("Azure Deployment Name", key="azure_deployment")
            
        return provider, model


def main(
    col1,
    col2,
    placeholder,
    config,
):
    """
    main loop
    params:

    col1 (int): size col 1
    col2 (int): size col 2
    placeholder (streamlit.empty): placeholder
    config: Configuration Dictionary
    """
    # two columns

    if "vcol1doc" in st.session_state and "vcol2doc" in st.session_state:
        col1 = st.session_state["vcol1doc"]
        col2 = st.session_state["vcol2doc"]

    row1_1, row1_2 = st.columns((col1, col2))
    try:
        # Initialize Vars
        # Initialice state
        if "init_run_1" not in st.session_state:
            st.session_state["init_run_1"] = False
        if st.session_state["init_run_1"] == False:
            init_session_1(st, ss, col1, col2)

        with row1_1:

            # Access the uploaded ref via a key.
            if st.session_state.value1 >= 0 and st.session_state["salir_1"] == False:
                uploaded_files = st.file_uploader(
                    "Upload PDF file",
                    type=("pdf"),
                    key="pdf",
                    accept_multiple_files=False,
                )  # accept_multiple_files=True,
                if uploaded_files:
                    logging.info(
                        f"Speak with PDF Page: file uploaded {uploaded_files.name}"
                    )
                if uploaded_files:
                    # To read file as bytes:
                    im_bytes = uploaded_files.getvalue()
                    file_path = f"{TMP_FOLDER}/{uploaded_files.name}"
                    with open(file_path, "wb") as f:
                        f.write(im_bytes)
                        f.close()
                    if ss.pdf:
                        ss.pdf_ref1 = im_bytes
                    numpages = count_pdf_pages(file_path)
                    logging.info(
                        f"Numero de paginas del fichero {uploaded_files.name} : {numpages}"
                    )
                    st.session_state["file_name1"] = file_path
                    st.session_state["file_history1"] = uploaded_files.name
                    st.session_state["upload_state1"] = (
                        f"Numero de paginas del fichero {uploaded_files.name} : {numpages}"
                    )

                    logging.info(
                        f"File path {file_path} File name {uploaded_files.name}"
                    )

                st.session_state.value1 = 1  # file uploaded

            # Now you can access "pdf_ref1" anywhere in your app.
            if ss.pdf_ref1:
                with row1_1:
                    if (
                        st.session_state.value1 >= 1
                        and st.session_state["salir_1"] == False
                    ):
                        binary_data = ss.pdf_ref1
                        if st.session_state["vcol1doc"] == 50:
                            width = 900
                        elif st.session_state["vcol1doc"] == 20:
                            width = 350
                        else:
                            width = 700
                        pdf_viewer(
                            input=binary_data, width=width, height=400, key="pdf_viewer"
                        )
                        if st.button(
                            "Parse pdf", on_click=click_button_parse, args=(st,)
                        ):
                            if st.session_state["vector_store1"] == None:
                                st.session_state["data1"] = docs_from_pymupdf4llm(
                                    st.session_state["file_name1"]
                                )
                                st.session_state["vector_store1"] = (
                                    vectorindex_from_data(
                                        data=st.session_state["data1"],
                                        embed_model=st.session_state["embeddings1"],
                                    )
                                )
                                logging.info(
                                    f"Number pages document {len(st.session_state['data1'])}"
                                )
                                # persist index
                                persist_index_to_disk(
                                    index=st.session_state["vector_store1"],
                                    path=st.session_state["db_local_folder1"],
                                )
                                logging.info("Vector Store created from document pages")
                                st.session_state["upload_state1"] = (
                                    f"Number pages document {len(st.session_state['data1'])}"
                                    + "\n"
                                    + "Vector Store created from document pages"
                                )

                        if (
                            st.session_state["click_button_parse1"] == True
                            and st.session_state["vector_store1"] != None
                            and st.session_state["salir_1"] == False
                        ):
                            logging.info(
                                f"Status bottom parse {st.session_state['click_button_parse1']}"
                            )
                            input_prompt = st.text_input(
                                "Introduce  query to the document 👇 👇",
                                key="pdf_query",
                            )
                            st.session_state["chat_true1"] = "chat activo"
                            if (
                                input_prompt
                                and st.session_state["salir_1"] == False
                                and st.session_state["chat_true1"] == "chat activo"
                            ):
                                if st.session_state["llamaindex1"] == None:
                                    st.session_state["llamaindex1"] = (
                                        create_chat_engine(
                                            st.session_state["vector_store1"]
                                        )
                                    )
                                response = st.session_state["llamaindex1"].chat(
                                    input_prompt
                                )
                                st.session_state["upload_state1"] = str(response)
                                st.session_state["chat_history1"].append(
                                    (input_prompt, str(response))
                                )

        with row1_2:
            if st.button("Salir", on_click=change_state_1, args=(st, placeholder)):

                logging.info("Salir and writing history")

                # del placeholder

            with st.expander(
                "️ Instruccion to send to Model 👇👇",
                expanded=st.session_state["expander_1"],
            ):
                _ = st.text_area(
                    "Status selection", "", key="upload_state1", height=500
                )

    except:

        # get the sys stack and log to gcloud
        st.session_state["salir_1"] = True
        placeholder.empty()
        text = print_stack()
        text = "Speak with PDF Page " + text
        logging.error(text)
    return


if __name__ == "__main__":
    global col1, col2
    st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
    # go to login page if not authenticated
    if (
        st.session_state["authentication_status"] == None
        or st.session_state["authentication_status"] == False
    ):
        st.session_state.runpage = "main.py"
        st.switch_page("main.py")
    if "salir_1" not in st.session_state:
        st.session_state["salir_1"] = False

    if st.session_state["salir_1"] == False:
        # Empty placeholder for session objects
        placeholder_1 = st.empty()
        with placeholder_1.container():
            col1, col2 = 50, 50
            ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
            path = Path(ROOT_DIR)
            config = dotenv_values(os.path.join(path.parent.absolute(), "keys", ".env"))

            # Initialize Model
            if "chat1" not in st.session_state:
                llm_provider = config.get("LLM_PROVIDER", "openai")
                
                if llm_provider == "openai":
                    os.environ["OPENAI_API_KEY"] = config.get("OPENAI_API_KEY")
                    st.session_state["chat1"] = get_llm(
                        provider="openai",
                        model=config.get("OPENAI_MODEL"),
                    )
                
                elif llm_provider == "claude":
                    os.environ["ANTHROPIC_API_KEY"] = config.get("ANTHROPIC_API_KEY")
                    st.session_state["chat1"] = get_llm(
                        provider="claude",
                        model=config.get("ANTHROPIC_MODEL"),
                    )
                
                elif llm_provider == "azure":
                    st.session_state["chat1"] = get_llm(
                        provider="azure",
                        model=config.get("AZURE_OPENAI_MODEL"),
                        deployment_name=config.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
                        api_base=config.get("AZURE_OPENAI_API_BASE"),
                        api_key=config.get("AZURE_OPENAI_API_KEY"),
                        api_version=config.get("AZURE_OPENAI_API_VERSION"),
                    )
            # Initialize embeddings models
            logging.info(f"Model {config.get('NVIDIA_MODEL')} initialized")
            # Nvidia embeddings model NVIDIA_EMBEDDINGS
            if "embeddings1" not in st.session_state:
                st.session_state["embeddings1"] = get_embeddings(
                    model=config["NVIDIA_EMBEDDINGS"],
                )
            logging.info(
                f"Model Embeddings: {config.get('NVIDIA_EMBEDDINGS')} initialized"
            )
            if "index1" not in st.session_state:
                st.session_state["index1"] = setup_index(
                    model=st.session_state["chat1"],
                    embeddings=st.session_state["embeddings1"],
                )
            logging.info("LLama Index  initialized")
            # check if we have the index presisted in the folder
            if "db_local_folder1" not in st.session_state:
                st.session_state["db_local_folder1"] = os.path.join(
                    path.parent.absolute(),
                    "saves",
                    config.get("INDEX_NAME"),
                )
            if "db_local_file1" not in st.session_state:
                st.session_state["db_local_file1"] = os.path.join(
                    path.parent.absolute(),
                    "saves",
                    config.get("INDEX_NAME"),
                    "default__vector_store.json",
                )
            # Initialize vector store
            if "vector_store1" not in st.session_state:
                st.session_state["vector_store1"] = None
            if (
                os.path.isfile(st.session_state["db_local_file1"])
                and st.session_state["vector_store1"] == None
            ):
                logging.info(
                    f"Loading Index from: {st.session_state['db_local_folder1']}"
                )
                st.session_state["vector_store1"] = load_index_from_disk(
                    st.session_state["db_local_folder1"]
                )
                logging.info(
                    f"Index from: {st.session_state['db_local_folder1']} Loaded"
                )
            elif (
                os.path.isfile(st.session_state["db_local_file1"]) == False
                and st.session_state["vector_store1"] == None
            ):
                logging.info("Index not found")
                st.session_state["vector_store1"] = None

            if "processor" not in st.session_state:
                st.session_state.processor = DistributedPDFProcessor()
                
            # Add batch upload support
            uploaded_files = st.file_uploader(
                "Upload PDF files",
                type=["pdf"],
                accept_multiple_files=True
            )
            
            if uploaded_files:
                with st.spinner("Processing PDFs..."):
                    for file in uploaded_files:
                        st.session_state.processor.queue_pdf(file)
                
            # Show processing status
            if "processor" in st.session_state:
                status = st.session_state.processor.get_status()
                st.write(f"Processed: {status['processed']}")
                st.write(f"Pending: {status['pending']}")

            main(
                col1=col1,
                col2=col2,
                placeholder=placeholder_1,
                config=config,
            )
