import json,csv,io
from datetime import datetime
from sqlalchemy import select
from fastapi import HTTPException
from src.models import ImprovementCase,CaseArchive,EfficiencyRun
from src.constants.enums import RunStatus,CaseStatus,ArchiveStatus
CSV_COLUMNS=['venue_code','venue_name','period','revision','theta','input_slack','output_surplus','projected_inputs','projected_outputs','peer_lambdas','hypothesis','verification','approved_by','approved_at','run_fingerprint']
def _get_case(db,id):
    item=db.get(ImprovementCase,id)
    if not item:raise HTTPException(404,'评议假设不存在')
    return item
def _archives(db,case_id):
    return db.scalars(select(CaseArchive).where(CaseArchive.case_id==case_id).order_by(CaseArchive.id.desc())).all()
def _archive_dict(a):
    return {'id':a.id,'case_id':a.case_id,'revision':a.revision,'title':a.title,'run_id':a.run_id,'observation_id':a.observation_id,'hypothesis':a.hypothesis,'verification':a.verification,'run_fingerprint':a.run_fingerprint,'snapshot':a.snapshot,'approved_by':a.approved_by,'approved_at':a.approved_at,'archive_status':a.archive_status,'withdrawn_at':a.withdrawn_at}
def _serialize(db,item):
    archives=_archives(db,item.id)
    effective=next((a for a in archives if a.archive_status==ArchiveStatus.EFFECTIVE),None)
    return {'id':item.id,'title':item.title,'run_id':item.run_id,'observation_id':item.observation_id,'hypothesis':item.hypothesis,'verification':item.verification,'status':item.status,'revision':item.revision,'approved_by':item.approved_by,'created_at':item.created_at,'updated_at':item.updated_at,'effective_archive_id':effective.id if effective else None,'archive_count':len(archives),'archives':[_archive_dict(a) for a in archives]}
def _stale(item,expected):
    if item.revision!=expected:
        raise HTTPException(409,f'版本冲突：您操作的是第{expected}版，当前已是第{item.revision}版，请刷新页面后按最新版本处理')
def _target_row(run,observation_id):
    return next((r for r in run.result['baseline'] if r['observation_id']==observation_id),None)
def list_cases(db):
    items=db.scalars(select(ImprovementCase).order_by(ImprovementCase.id.desc())).all()
    return [_serialize(db,item) for item in items]
def create_case(db,data):
    run=db.get(EfficiencyRun,data.run_id)
    if not run or run.status!=RunStatus.COMPLETED:raise HTTPException(422,'请选择已完成研究')
    if not _target_row(run,data.observation_id):raise HTTPException(422,'机构观察不属于该研究的同期目标集')
    if db.scalar(select(ImprovementCase).where(ImprovementCase.title==data.title)):raise HTTPException(409,'假设标题已存在')
    item=ImprovementCase(**data.model_dump(),status=CaseStatus.DRAFT,revision=1)
    db.add(item);db.commit();db.refresh(item)
    return _serialize(db,item)
def revise_case(db,id,data,user):
    item=_get_case(db,id)
    if item.status==CaseStatus.APPROVED:raise HTTPException(409,'已批准的有效评议不能直接修订，请先撤回后再重议')
    _stale(item,data.expected_revision)
    if data.title!=item.title and db.scalar(select(ImprovementCase).where(ImprovementCase.title==data.title,ImprovementCase.id!=id)):
        raise HTTPException(409,'假设标题已存在')
    item.title=data.title;item.hypothesis=data.hypothesis;item.verification=data.verification
    item.revision+=1
    # 撤回后重议：重新进入待评议，旧档案保持 withdrawn 不变
    if item.status==CaseStatus.WITHDRAWN:item.status=CaseStatus.DRAFT
    db.commit();db.refresh(item)
    return _serialize(db,item)
def approve_case(db,id,payload,user):
    item=_get_case(db,id)
    if item.status==CaseStatus.APPROVED:raise HTTPException(409,'该版本已批准，无需重复批准')
    _stale(item,payload.expected_revision)
    run=db.get(EfficiencyRun,item.run_id)
    if not run or run.status!=RunStatus.COMPLETED:raise HTTPException(422,'依据研究未完成，不能批准')
    row=_target_row(run,item.observation_id)
    if not row:raise HTTPException(422,'机构观察不属于该研究的同期目标集')
    # 固定批准当时的机构投影：整行口径连同期间、参照λ一起快照，之后不再随研究读取而变化
    snapshot={k:row.get(k) for k in ('observation_id','venue_code','venue_name','theta','strong_efficient','zero_output','input_slack','output_slack','projected_inputs','projected_outputs','peers','source')}
    snapshot['period']=run.result.get('period');snapshot['benchmark_name']=run.result.get('benchmark_name')
    # 防御性处理：若存在未撤回的有效档案，先标记为被替代，保证同一时间只有一个有效版
    for old in db.scalars(select(CaseArchive).where(CaseArchive.case_id==id,CaseArchive.archive_status==ArchiveStatus.EFFECTIVE)).all():
        old.archive_status=ArchiveStatus.SUPERSEDED
    archive=CaseArchive(case_id=id,revision=item.revision,title=item.title,run_id=item.run_id,observation_id=item.observation_id,hypothesis=item.hypothesis,verification=item.verification,run_fingerprint=run.result.get('fingerprint',''),snapshot=snapshot,approved_by=user.email,approved_at=datetime.utcnow(),archive_status=ArchiveStatus.EFFECTIVE)
    db.add(archive)
    item.status=CaseStatus.APPROVED;item.approved_by=user.email
    db.commit();db.refresh(archive);db.refresh(item)
    return _serialize(db,item)
def withdraw_case(db,id,payload,user):
    item=_get_case(db,id)
    if item.status!=CaseStatus.APPROVED:raise HTTPException(409,'仅已批准的有效评议可以撤回')
    _stale(item,payload.expected_revision)
    effective=db.scalars(select(CaseArchive).where(CaseArchive.case_id==id,CaseArchive.archive_status==ArchiveStatus.EFFECTIVE)).all()
    now=datetime.utcnow()
    for archive in effective:
        archive.archive_status=ArchiveStatus.WITHDRAWN;archive.withdrawn_at=now
    item.status=CaseStatus.WITHDRAWN
    db.commit();db.refresh(item)
    return _serialize(db,item)
def list_archives(db,id,user):
    if user.role!='admin':raise HTTPException(403,'历史档案仅评议负责人可追溯')
    _get_case(db,id)
    return [_archive_dict(a) for a in _archives(db,id)]
def _safe(value):
    text=str(value)
    return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
def _csv_from_archive(archive):
    row=archive.snapshot
    out=io.StringIO();out.write('\ufeff');writer=csv.writer(out);writer.writerow(CSV_COLUMNS)
    writer.writerow([_safe(row.get('venue_code','')),_safe(row.get('venue_name','')),_safe(row.get('period','')),archive.revision,row.get('theta'),json.dumps(row.get('input_slack',{}),ensure_ascii=False),json.dumps(row.get('output_slack',{}),ensure_ascii=False),json.dumps(row.get('projected_inputs',{}),ensure_ascii=False),json.dumps(row.get('projected_outputs',{}),ensure_ascii=False),json.dumps(row.get('peers',[]),ensure_ascii=False),_safe(archive.hypothesis),_safe(archive.verification),_safe(archive.approved_by),archive.approved_at.isoformat() if archive.approved_at else '',archive.run_fingerprint])
    return out.getvalue()
def export_case(db,id,user):
    item=_get_case(db,id)
    archive=db.scalar(select(CaseArchive).where(CaseArchive.case_id==id,CaseArchive.archive_status==ArchiveStatus.EFFECTIVE).order_by(CaseArchive.id.desc()))
    if not archive:raise HTTPException(409,'当前没有有效批准版，撤回或待评议期间不能下载交付')
    return _csv_from_archive(archive),archive.revision
def export_archive(db,id,archive_id,user):
    if user.role!='admin':raise HTTPException(403,'历史版本仅评议负责人可追溯下载')
    _get_case(db,id)
    archive=db.get(CaseArchive,archive_id)
    if not archive or archive.case_id!=id:raise HTTPException(404,'获批档案不存在')
    return _csv_from_archive(archive),archive.revision
