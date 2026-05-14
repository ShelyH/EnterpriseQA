"""
加权 RRF 混合检索器（EnsembleRetriever）。

来源：LangChain 0.3.x（MIT），仅依赖 langchain_core，避免
`from langchain.retrievers import EnsembleRetriever` 触发的
langchain.retrievers 包级导入链（其中 chains/base 依赖已移除的
langchain_core.memory）。
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Hashable, Iterable, Iterator
from itertools import chain
from typing import Any, Callable, Optional, TypeVar, cast

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever, RetrieverLike
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import ensure_config, patch_config
from langchain_core.runnables.utils import (
    ConfigurableFieldSpec,
    get_unique_config_specs,
)
from pydantic import model_validator

T = TypeVar("T")
H = TypeVar("H", bound=Hashable)


def unique_by_key(iterable: Iterable[T], key: Callable[[T], H]) -> Iterator[T]:
    """按 key 去重，保留首次出现的元素。"""
    seen: set[H] = set()
    for e in iterable:
        k = key(e)
        if k not in seen:
            seen.add(k)
            yield e


class EnsembleRetriever(BaseRetriever):
    """对多个检索器结果做加权倒数排名融合（RRF）。"""

    retrievers: list[RetrieverLike]
    weights: list[float]
    c: int = 60
    id_key: Optional[str] = None

    @property
    def config_specs(self) -> list[ConfigurableFieldSpec]:
        return get_unique_config_specs(
            spec for retriever in self.retrievers for spec in retriever.config_specs
        )

    @model_validator(mode="before")
    @classmethod
    def set_weights(cls, values: dict[str, Any]) -> Any:
        if not values.get("weights"):
            n_retrievers = len(values["retrievers"])
            values["weights"] = [1 / n_retrievers] * n_retrievers
        return values

    def invoke(
        self, input: str, config: Optional[RunnableConfig] = None, **kwargs: Any
    ) -> list[Document]:
        from langchain_core.callbacks import CallbackManager

        config = ensure_config(config)
        callback_manager = CallbackManager.configure(
            config.get("callbacks"),
            None,
            verbose=kwargs.get("verbose", False),
            inheritable_tags=config.get("tags", []),
            local_tags=self.tags,
            inheritable_metadata=config.get("metadata", {}),
            local_metadata=self.metadata,
        )
        run_manager = callback_manager.on_retriever_start(
            None,
            input,
            name=config.get("run_name") or self.get_name(),
            **kwargs,
        )
        try:
            result = self.rank_fusion(input, run_manager=run_manager, config=config)
        except Exception as e:
            run_manager.on_retriever_error(e)
            raise e
        else:
            run_manager.on_retriever_end(result, **kwargs)
        return result

    async def ainvoke(
        self, input: str, config: Optional[RunnableConfig] = None, **kwargs: Any
    ) -> list[Document]:
        from langchain_core.callbacks import AsyncCallbackManager

        config = ensure_config(config)
        callback_manager = AsyncCallbackManager.configure(
            config.get("callbacks"),
            None,
            verbose=kwargs.get("verbose", False),
            inheritable_tags=config.get("tags", []),
            local_tags=self.tags,
            inheritable_metadata=config.get("metadata", {}),
            local_metadata=self.metadata,
        )
        run_manager = await callback_manager.on_retriever_start(
            None,
            input,
            name=config.get("run_name") or self.get_name(),
            **kwargs,
        )
        try:
            result = await self.arank_fusion(
                input, run_manager=run_manager, config=config
            )
        except Exception as e:
            await run_manager.on_retriever_error(e)
            raise e
        else:
            await run_manager.on_retriever_end(result, **kwargs)
        return result

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return self.rank_fusion(query, run_manager)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return await self.arank_fusion(query, run_manager)

    def rank_fusion(
        self,
        query: str,
        run_manager: CallbackManagerForRetrieverRun,
        *,
        config: Optional[RunnableConfig] = None,
    ) -> list[Document]:
        retriever_docs = [
            retriever.invoke(
                query,
                patch_config(
                    config, callbacks=run_manager.get_child(tag=f"retriever_{i + 1}")
                ),
            )
            for i, retriever in enumerate(self.retrievers)
        ]

        for i in range(len(retriever_docs)):
            retriever_docs[i] = [
                Document(page_content=cast(str, doc)) if isinstance(doc, str) else doc
                for doc in retriever_docs[i]
            ]

        return self.weighted_reciprocal_rank(retriever_docs)

    async def arank_fusion(
        self,
        query: str,
        run_manager: AsyncCallbackManagerForRetrieverRun,
        *,
        config: Optional[RunnableConfig] = None,
    ) -> list[Document]:
        retriever_docs = await asyncio.gather(
            *[
                retriever.ainvoke(
                    query,
                    patch_config(
                        config,
                        callbacks=run_manager.get_child(tag=f"retriever_{i + 1}"),
                    ),
                )
                for i, retriever in enumerate(self.retrievers)
            ]
        )

        for i in range(len(retriever_docs)):
            retriever_docs[i] = [
                Document(page_content=doc) if not isinstance(doc, Document) else doc
                for doc in retriever_docs[i]
            ]

        return self.weighted_reciprocal_rank(retriever_docs)

    def weighted_reciprocal_rank(
        self, doc_lists: list[list[Document]]
    ) -> list[Document]:
        if len(doc_lists) != len(self.weights):
            raise ValueError(
                "Number of rank lists must be equal to the number of weights."
            )

        rrf_score: dict[str, float] = defaultdict(float)
        for doc_list, weight in zip(doc_lists, self.weights):
            for rank, doc in enumerate(doc_list, start=1):
                key = (
                    doc.page_content
                    if self.id_key is None
                    else doc.metadata[self.id_key]
                )
                rrf_score[key] += weight / (rank + self.c)

        all_docs = chain.from_iterable(doc_lists)
        sorted_docs = sorted(
            unique_by_key(
                all_docs,
                lambda doc: (
                    doc.page_content
                    if self.id_key is None
                    else doc.metadata[self.id_key]
                ),
            ),
            reverse=True,
            key=lambda doc: rrf_score[
                doc.page_content
                if self.id_key is None
                else doc.metadata[self.id_key]
            ],
        )
        return list(sorted_docs)
