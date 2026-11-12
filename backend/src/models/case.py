from sqlalchemy import ForeignKey,String,Integer,JSON,DateTime
from sqlalchemy.orm import Mapped,mapped_column
from datetime import datetime
from src.config.database import Base
class ImprovementCase(Base):
    __tablename__='improvement_cases'
    id:Mapped[int]=mapped_column(primary_key=True)
    title:Mapped[str]=mapped_column(String(160),unique=True)
    run_id:Mapped[int]=mapped_column(ForeignKey('efficiency_runs.id'))
    observation_id:Mapped[int]=mapped_column(ForeignKey('period_observations.id'))
    hypothesis:Mapped[str]=mapped_column(String(1200))
    verification:Mapped[str]=mapped_column(String(1000))
    status:Mapped[str]=mapped_column(String(20),default='draft')
    # 当前草稿版本号：每次保存修订递增，用于乐观并发控制；批准即固定该版本
    revision:Mapped[int]=mapped_column(Integer,default=1)
    approved_by:Mapped[str]=mapped_column(String(160),default='')
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class CaseArchive(Base):
    """获批档案：每次批准生成一条不可变快照，撤回只改状态不改写内容。"""
    __tablename__='case_archives'
    id:Mapped[int]=mapped_column(primary_key=True)
    case_id:Mapped[int]=mapped_column(ForeignKey('improvement_cases.id'),index=True)
    revision:Mapped[int]=mapped_column(Integer)
    title:Mapped[str]=mapped_column(String(160))
    run_id:Mapped[int]=mapped_column(ForeignKey('efficiency_runs.id'))
    observation_id:Mapped[int]=mapped_column(ForeignKey('period_observations.id'))
    hypothesis:Mapped[str]=mapped_column(String(1200))
    verification:Mapped[str]=mapped_column(String(1000))
    # 批准当时固定的研究指纹
    run_fingerprint:Mapped[str]=mapped_column(String(80),default='')
    # 批准当时固定的机构投影与评议数据（机构口径、θ、松弛、盈余、参照λ）
    snapshot:Mapped[dict]=mapped_column(JSON,default=dict)
    approved_by:Mapped[str]=mapped_column(String(160))
    approved_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    # effective=当前有效；withdrawn=已撤回；superseded=被后续批准替代的历史档案
    archive_status:Mapped[str]=mapped_column(String(20),default='effective',index=True)
    withdrawn_at:Mapped[datetime]=mapped_column(DateTime,nullable=True)
