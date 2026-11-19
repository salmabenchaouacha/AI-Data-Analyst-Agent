from functools import lru_cache

from langchain.chat_models import init_chat_model

from .config import settings


@lru_cache
def agent_llm():
    # temperature 0 -> reproducible evaluation runs
    return init_chat_model(settings.agent_model, temperature=0)


@lru_cache
def judge_llm():
    return init_chat_model(settings.judge_model, temperature=0)
