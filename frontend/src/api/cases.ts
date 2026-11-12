import {request,post} from './client';
import type {Case,CaseArchive} from '../types/domain';
export const getCases=()=>request<Case[]>('/cases');
export const createCase=(data:unknown)=>post<Case>('/cases',data);
export const reviseCase=(id:number,data:unknown)=>request<Case>('/cases/'+id,{method:'PATCH',body:JSON.stringify(data)});
export const approveCase=(id:number,expected_revision:number)=>request<Case>('/cases/'+id+'/approve',{method:'PATCH',body:JSON.stringify({expected_revision})});
export const withdrawCase=(id:number,expected_revision:number)=>request<Case>('/cases/'+id+'/withdraw',{method:'PATCH',body:JSON.stringify({expected_revision})});
export const getArchives=(id:number)=>request<CaseArchive[]>('/cases/'+id+'/archives');
async function download(url:string,filename:string){
  const r=await fetch(url,{headers:{Authorization:'Bearer '+localStorage.getItem('frontier-token')}});
  if(!r.ok){const e=await r.json().catch(()=>({detail:'下载失败'}));throw new Error(typeof e.detail==='string'?e.detail:JSON.stringify(e.detail));}
  const link=URL.createObjectURL(await r.blob());
  const a=document.createElement('a');a.href=link;a.download=filename;a.click();URL.revokeObjectURL(link);
}
// 联络员与负责人都只能取当前有效批准版；无有效版时后端拒绝
export const exportCase=(id:number)=>download(`/api/cases/${id}/export`,`qiyuan-case-${id}-effective.csv`);
// 历史档案仅负责人可追溯下载
export const exportArchive=(id:number,archiveId:number,revision:number)=>download(`/api/cases/${id}/archives/${archiveId}/export`,`qiyuan-case-${id}-v${revision}-archive-${archiveId}.csv`);
