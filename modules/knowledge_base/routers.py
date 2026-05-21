# from fastapi import APIRouter, Depends, HTTPException, status
# from openai import AsyncOpenAI
# from pydantic import BaseModel
# from sqlmodel.ext.asyncio.session import AsyncSession
#
# from modules.knowledge_base.models import KnowledgeBase, KnowledgeBaseTypeEnum
# from modules.knowledge_base.services import (
#     add_knowledge_base,
#     delete_all_knowledge_bases,
#     delete_knowledge_base,
#     get_knowledge_base_list,
# )
# from utils.database import get_session
#
#
# router = APIRouter()
#
#
# class KnowledgeBaseItemModel(BaseModel):
#     type: KnowledgeBaseTypeEnum
#     title: str
#     content: str
#
#
# class KnowledgeBaseRequestModel(BaseModel):
#     knowledge_bases: list[KnowledgeBaseItemModel]
#
#
# class KnowledgeBaseResponseModel(BaseModel):
#     id: int
#     type: KnowledgeBaseTypeEnum
#     title: str
#     content: str
#
#
# @router.get("/", response_model=list[KnowledgeBaseResponseModel])
# async def list_knowledge_base(
#     session: AsyncSession = Depends(get_session),
# ):
#     data = await get_knowledge_base_list(session)
#     return data
#
#
# @router.delete("/delete-all")
# async def delete_all_knowledge_base(session: AsyncSession = Depends(get_session)):
#     await delete_all_knowledge_bases(session)
#
#
# @router.delete("/{knowledge_base_id}")
# async def delete_knowledge_base(
#     knowledge_base_id: int, session: AsyncSession = Depends(get_session)
# ):
#     knowledge_base_id = await delete_knowledge_base(session, knowledge_base_id)
#     if not knowledge_base_id:
#         raise HTTPException(status.HTTP_404_NOT_FOUND)
#     return knowledge_base_id
#
#
# @router.post("/")
# async def create_knowledge_base(data: KnowledgeBaseRequestModel, session: AsyncSession = Depends(get_session)):
#     openai = AsyncOpenAI()
#
#     for knowledge_base_item in data.knowledge_bases:
#         text = f"type: {knowledge_base_item.type.value}\ntitle: {knowledge_base_item.title}\ncontent: {knowledge_base_item.content}"
#         embedding_response = await openai.embeddings.create(
#             input=text,
#             model="text-embedding-3-small",
#         )
#         embedding = embedding_response.data[0].embedding
#
#         new_knowledge_base = KnowledgeBase(
#             type=knowledge_base_item.type,
#             title=knowledge_base_item.title,
#             content=knowledge_base_item.content,
#             embedding=embedding,
#         )
#         await add_knowledge_base(session, new_knowledge_base)
