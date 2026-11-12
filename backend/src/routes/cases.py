from fastapi import APIRouter,Depends,Response
from src.config.database import get_db
from src.utils.auth import current_user,editor,admin
from src.schemas.case import CaseInput,CaseRevisionInput,ApproveInput,WithdrawInput
from src.controllers.case_controller import list_cases,create_case,revise_case,approve_case,withdraw_case,list_archives,export_case,export_archive
router=APIRouter(prefix='/cases')
@router.get('')
def index(db=Depends(get_db),user=Depends(current_user)):return list_cases(db)
@router.post('',status_code=201)
def create(data:CaseInput,db=Depends(get_db),user=Depends(editor)):return create_case(db,data)
@router.patch('/{id}')
def revise(id:int,data:CaseRevisionInput,db=Depends(get_db),user=Depends(editor)):return revise_case(db,id,data,user)
@router.patch('/{id}/approve')
def approve(id:int,payload:ApproveInput,db=Depends(get_db),user=Depends(admin)):return approve_case(db,id,payload,user)
@router.patch('/{id}/withdraw')
def withdraw(id:int,payload:WithdrawInput,db=Depends(get_db),user=Depends(admin)):return withdraw_case(db,id,payload,user)
@router.get('/{id}/archives')
def archives(id:int,db=Depends(get_db),user=Depends(admin)):return list_archives(db,id,user)
@router.get('/{id}/export')
def export(id:int,db=Depends(get_db),user=Depends(current_user)):
    content,revision=export_case(db,id,user)
    return Response(content,media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="venue-case-{id}-v{revision}.csv"'})
@router.get('/{id}/archives/{archive_id}/export')
def export_history(id:int,archive_id:int,db=Depends(get_db),user=Depends(admin)):
    content,revision=export_archive(db,id,archive_id,user)
    return Response(content,media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="venue-case-{id}-v{revision}-archive-{archive_id}.csv"'})
