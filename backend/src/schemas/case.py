from pydantic import BaseModel,Field
class CaseInput(BaseModel):
    title:str=Field(min_length=2,max_length=160)
    run_id:int
    observation_id:int
    hypothesis:str=Field(min_length=10,max_length=1200)
    verification:str=Field(min_length=10,max_length=1000)
class CaseRevisionInput(BaseModel):
    title:str=Field(min_length=2,max_length=160)
    hypothesis:str=Field(min_length=10,max_length=1200)
    verification:str=Field(min_length=10,max_length=1000)
    # 修改者看到的版本号；与服务端当前版本不一致即并发冲突
    expected_revision:int=Field(ge=1)
class ApproveInput(BaseModel):
    # 负责人看到的版本号；批准旧稿时返回409冲突
    expected_revision:int=Field(ge=1)
class WithdrawInput(BaseModel):
    # 撤回同样按看到的版本操作，防止撤回期间已有新修订
    expected_revision:int=Field(ge=1)
