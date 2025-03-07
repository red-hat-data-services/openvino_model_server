#*****************************************************************************
# Copyright 2023 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#*****************************************************************************

# This entire file is for customization depending on the LLM model.
# More info: https://github.com/openvinotoolkit/openvino_notebooks/blob/main/notebooks/254-llm-chatbot/config.py

from transformers import (
    StoppingCriteria,
    StoppingCriteriaList,
)
import torch

DEFAULT_SYSTEM_PROMPT = """\
You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe.  Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.
If a question does not make any sense or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.\
"""

DEFAULT_SYSTEM_PROMPT_JAPANESE = """\
あなたは親切で、礼儀正しく、誠実なアシスタントです。 常に安全を保ちながら、できるだけ役立つように答えてください。 回答には、有害、非倫理的、人種差別的、性差別的、有毒、危険、または違法なコンテンツを含めてはいけません。 回答は社会的に偏見がなく、本質的に前向きなものであることを確認してください。
質問が意味をなさない場合、または事実に一貫性がない場合は、正しくないことに答えるのではなく、その理由を説明してください。 質問の答えがわからない場合は、誤った情報を共有しないでください。\
"""

DEFAULT_RAG_PROMPT = """\
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.\
"""

DEFAULT_RAG_PROMPT_CHINESE = """\
基于以下已知信息，请简洁并专业地回答用户的问题。如果无法从中得到答案，请说 "根据已知信息无法回答该问题" 或 "没有提供足够的相关信息"。不允许在答案中添加编造成分。另外，答案请使用中文。\
"""


def red_pijama_partial_text_processor(partial_text, new_text):
    if new_text == "<":
        return partial_text

    partial_text += new_text
    return partial_text.split("<bot>:")[-1]


def llama_partial_text_processor(partial_text, new_text):
    new_text = new_text.replace("[INST]", "").replace("[/INST]", "")
    partial_text += new_text
    return partial_text


def chatglm_partial_text_processor(partial_text, new_text):
    new_text = new_text.strip()
    new_text = new_text.replace("[[训练时间]]", "2023年")
    partial_text += new_text
    return partial_text


def youri_partial_text_processor(partial_text, new_text):
    new_text = new_text.replace("システム:", "")
    partial_text += new_text
    return partial_text


SUPPORTED_LLM_MODELS = {
    "tiny-llama-1b-chat": {
        "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v0.6",
        "remote": False,
        "start_message": f"<|system|>\n{DEFAULT_SYSTEM_PROMPT}</s>\n",
        "history_template": "<|user|>\n{user}</s> \n<|assistant|>\n{assistant}</s> \n",
        "current_message_template": "<|user|>\n{user}</s> \n<|assistant|>\n{assistant}",
        "prompt_template": f"""<|system|> {DEFAULT_RAG_PROMPT }</s>"""
        + """
        <|user|>
        Question: {question} 
        Context: {context} 
        Answer: </s>
        <|assistant|>""",
    },
    "red-pajama-3b-chat": {
        "model_id": "togethercomputer/RedPajama-INCITE-Chat-3B-v1",
        "remote": False,
        "start_message": "",
        "history_template": "\n<human>:{user}\n<bot>:{assistant}",
        "stop_tokens": [29, 0],
        "partial_text_processor": red_pijama_partial_text_processor,
        "current_message_template": "\n<human>:{user}\n<bot>:{assistant}",
        "prompt_template": f"""{DEFAULT_RAG_PROMPT }"""
        + """
        <human>: Question: {question} 
        Context: {context} 
        Answer: <bot>""",
    },
    "llama-2-chat-7b": {
        "model_id": "meta-llama/Llama-2-7b-chat-hf",
        "remote": False,
        "start_message": f"<s>[INST] <<SYS>>\n{DEFAULT_SYSTEM_PROMPT }\n<</SYS>>\n\n",
        "history_template": "{user}[/INST]{assistant}</s><s>[INST]",
        "current_message_template": "{user} [/INST]{assistant}",
        "tokenizer_kwargs": {"add_special_tokens": False},
        "partial_text_processor": llama_partial_text_processor,
        "prompt_template": f"""[INST]Human: <<SYS>> {DEFAULT_RAG_PROMPT }<</SYS>>"""
        + """
        Question: {question} 
        Context: {context} 
        Answer: [/INST]""",
    },
    "mistral-7b": {
        "model_id": "mistralai/Mistral-7B-v0.1",
        "remote": False,
        "start_message": f"<s>[INST] <<SYS>>\n{DEFAULT_SYSTEM_PROMPT }\n<</SYS>>\n\n",
        "history_template": "{user}[/INST]{assistant}</s><s>[INST]",
        "current_message_template": "{user} [/INST]{assistant}",
        "tokenizer_kwargs": {"add_special_tokens": False},
        "partial_text_processor": llama_partial_text_processor,
        "prompt_template": f"""<s> [INST] {DEFAULT_RAG_PROMPT } [/INST] </s>"""
        + """ 
        [INST] Question: {question} 
        Context: {context} 
        Answer: [/INST]""",
    },
    "zephyr-7b-beta": {
        "model_id": "HuggingFaceH4/zephyr-7b-beta",
        "remote": False,
        "start_message": f"<|system|>\n{DEFAULT_SYSTEM_PROMPT}</s>\n",
        "history_template": "<|user|>\n{user}</s> \n<|assistant|>\n{assistant}</s> \n",
        "current_message_template": "<|user|>\n{user}</s> \n<|assistant|>\n{assistant}",
        "prompt_template": f"""<|system|> {DEFAULT_RAG_PROMPT }</s>"""
        + """ 
        <|user|>
        Question: {question} 
        Context: {context} 
        Answer: </s>
        <|assistant|>""",
    },
    "neural-chat-7b-v3-1": {
        "model_id": "Intel/neural-chat-7b-v3-1",
        "remote": False,
        "start_message": f"<s>[INST] <<SYS>>\n{DEFAULT_SYSTEM_PROMPT }\n<</SYS>>\n\n",
        "history_template": "{user}[/INST]{assistant}</s><s>[INST]",
        "current_message_template": "{user} [/INST]{assistant}",
        "tokenizer_kwargs": {"add_special_tokens": False},
        "partial_text_processor": llama_partial_text_processor,
        "prompt_template": f"""<s> [INST] {DEFAULT_RAG_PROMPT } [/INST] </s>"""
        + """
        [INST] Question: {question} 
        Context: {context} 
        Answer: [/INST]""",
    },
    "notus-7b-v1": {
        "model_id": "argilla/notus-7b-v1",
        "remote": False,
        "start_message": f"<|system|>\n{DEFAULT_SYSTEM_PROMPT}</s>\n",
        "history_template": "<|user|>\n{user}</s> \n<|assistant|>\n{assistant}</s> \n",
        "current_message_template": "<|user|>\n{user}</s> \n<|assistant|>\n{assistant}",
        "prompt_template": f"""<|system|> {DEFAULT_RAG_PROMPT }</s>"""
        + """
        <|user|>
        Question: {question} 
        Context: {context} 
        Answer: </s>
        <|assistant|>""",
    },
    "youri-7b-chat": {
        "model_id": "rinna/youri-7b-chat",
        "remote": False,
        "start_message": f"設定: {DEFAULT_SYSTEM_PROMPT_JAPANESE}\n",
        "history_template": "ユーザー: {user}\nシステム: {assistant}\n",
        "current_message_template": "ユーザー: {user}\nシステム: {assistant}",
        "tokenizer_kwargs": {"add_special_tokens": False},
        "partial_text_processor": youri_partial_text_processor,
    },
}

SUPPORTED_EMBEDDING_MODELS = {
    "all-mpnet-base-v2": {
        "model_id": "sentence-transformers/all-mpnet-base-v2",
        "do_norm": True,
    },
    "text2vec-large-chinese": {
        "model_id": "GanymedeNil/text2vec-large-chinese",
        "do_norm": False,
    },
}